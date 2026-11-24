"""Static syntax analysis of untrusted source; no source execution or imports."""
import ast
from functools import lru_cache
from pathlib import PurePosixPath
import re

from common import HERE,OLD

VERSION='content-static-v6-global-annotation'
LANGUAGES={'.py':'python','.pyi':'python','.js':'javascript','.mjs':'javascript','.cjs':'javascript','.jsx':'tsx','.ts':'typescript','.tsx':'tsx','.java':'java','.go':'go','.rs':'rust','.cs':'csharp','.dart':'dart','.sh':'bash','.bash':'bash','.rb':'ruby','.php':'php','.c':'c','.h':'c','.cc':'cpp','.cpp':'cpp','.hpp':'cpp','.kt':'kotlin','.scala':'scala','.html':'html','.vue':'vue','.svelte':'svelte','.feature':'gherkin','.robot':'robot','.bats':'bash'}
EXTRA_SOURCE={'.hs','.ml','.mli','.r','.jl','.pl','.pm','.f','.f90','.ipynb','.swift','.ex','.exs','.erl','.clj','.cljs','.lua','.ps1','.fs','.zig','.sol','.v','.vb','.sql'}
LANGUAGES.update({'.kt':'kotlin','.kts':'kotlin'})
DOCUMENT={'.md','.mdx','.rst','.txt','.adoc','.pdf','.svg','.json','.jsonl','.csv','.tsv','.yaml','.yml','.toml','.xml','.png','.jpg','.jpeg','.gif','.webp','.lock','.sum','.map','.snap'}
TEST_DIRS={'tests','test','__tests__','spec','testthat','unittests','unit_tests','integration-tests','integration_tests','e2e','androidtest','unittest'}


def language(path):return LANGUAGES.get(PurePosixPath(path).suffix.lower(),'unknown')


def eligible(path):
    p=PurePosixPath(path);ext=p.suffix.lower()
    if p.name.lower() in {'.gitkeep','.keep','.gitignore','.gitattributes','.editorconfig','.vscodeignore','.dockerignore','.npmignore','.eslintignore','.prettierignore','license','notice','authors','changelog','readme'}:return False
    if ext in DOCUMENT:return False
    return ext in LANGUAGES or ext in EXTRA_SOURCE or ext in OLD.SOURCE_EXTENSIONS or not ext or p.name in {'Dockerfile','Makefile','Justfile'}


def priority(path):
    p=PurePosixPath(path)
    parts={x.lower() for x in p.parts[:-1]}
    if parts & TEST_DIRS:return 0
    if OLD.classify_test_file(path)[0] or re.search(r'(?:test|spec)',p.stem,re.I):return 1
    return 2


def result(category,lang,reason,evidence=(),complete=True,**extra):
    return {'classification':category,'has_executable_tests':True if category=='automated_test' else None if category=='uncertain' else False,'language':lang,'evidence':list(evidence),'reason':reason,'needs_review':category=='uncertain','method':'deterministic','classifier_version':VERSION,'full_content_examined':complete,**extra}


def python_analysis(text,path):
    try:tree=ast.parse(text)
    except (SyntaxError,ValueError,RecursionError):return result('uncertain','python','Python syntax could not be parsed completely')
    parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    def call_name(node):
        try:return ast.unparse(node)
        except Exception:return ''
    imports=' '.join(call_name(x) for x in ast.walk(tree) if isinstance(x,(ast.Import,ast.ImportFrom)))
    def unimplemented(fn):
        body=[x for x in fn.body if not isinstance(x,ast.Expr) or not isinstance(x.value,ast.Constant) or not isinstance(x.value.value,str)]
        return not body or all(isinstance(x,ast.Pass) or isinstance(x,ast.Expr) and isinstance(x.value,ast.Constant) and x.value.value is Ellipsis or isinstance(x,ast.Raise) and 'NotImplementedError' in call_name(x) for x in body)
    candidates=[];support=[];dynamic=False
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and call_name(node.func) in {'exec','eval','unittest.defaultTestLoader.loadTestsFromName','pytest.main'}:dynamic=True
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            if any('fixture' in call_name(d) for d in node.decorator_list):support.append(node.name);continue
            owner=parents.get(node)
            unittest_owner=isinstance(owner,ast.ClassDef) and any('TestCase' in call_name(b) for b in owner.bases)
            if any('given' in call_name(d) for d in node.decorator_list) and not node.name.startswith('test'):dynamic=True
            if node.name.startswith('test_') or node.name=='test' or node.name=='runTest' and unittest_owner:
                if isinstance(owner,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
                ancestor=parents.get(node);unreachable=False
                while ancestor is not None:
                    if isinstance(ancestor,ast.If) and isinstance(ancestor.test,ast.Constant) and ancestor.test.value is False:unreachable=True
                    ancestor=parents.get(ancestor)
                if unreachable:continue
                candidates.append(node)
                if unimplemented(node):continue
                if isinstance(owner,ast.ClassDef) and not (owner.name.startswith('Test') or any('TestCase' in call_name(b) for b in owner.bases)):continue
                if any(re.search(r'\.(?:skip|skipif|xfail)\b',call_name(d)) for d in node.decorator_list):continue
                assertions=[n for n in ast.walk(node) if isinstance(n,ast.Assert) or isinstance(n,ast.Call) and re.search(r'(?:^|\.)(?:assert\w*|raises|warns|fail)$',call_name(n.func))]
                if assertions:
                    return result('automated_test','python','Implemented test function/method containing an assertion or expected-failure check',[{'symbol':node.name,'line':node.lineno,'kind':'test_function'},{'symbol':call_name(assertions[0].func) if isinstance(assertions[0],ast.Call) else 'assert','line':assertions[0].lineno,'kind':'assertion'}])
            if node.name in {'setUp','tearDown','setUpClass','tearDownClass'}:support.append(node.name)
    if candidates:
        if all(unimplemented(fn) for fn in candidates):return result('test_support','python','Only unimplemented test templates; no executable test bodies')
        return result('uncertain','python','Test-like functions have bodies, but static assertion/registration evidence is incomplete')
    if dynamic:return result('uncertain','python','Dynamic test loading or code generation requires contextual classification')
    if support or any(x in imports for x in ['pytest','unittest','hypothesis']):return result('test_support','python','Framework/fixture/setup code without implemented test cases')
    return result('not_test','python','Complete Python AST has no test cases or test-runner registration')


@lru_cache(maxsize=24)
def parser_for(lang):
    import tree_sitter_language_pack as pack
    pack.configure(pack.PackConfig(cache_dir=str(HERE/'.parser_cache')))
    return pack.get_parser(lang)


def walk(node):
    stack=[node]
    while stack:
        current=stack.pop();yield current
        stack.extend(reversed(current.named_children))


def code_mask(root,raw):
    data=bytearray(raw)
    def erase(n):
        if 'comment' in n.type or n.type in {'string','string_literal','interpreted_string_literal','raw_string_literal','template_string','character_literal','string_content'}:
            for i in range(n.start_byte,n.end_byte):
                if data[i] not in (10,13):data[i]=32
            return
        for c in n.named_children:erase(c)
    erase(root)
    return bytes(data).decode('utf-8',errors='replace')


def tree_analysis(text,path,lang):
    try:
        raw=text.encode('utf-8');root=parser_for(lang).parse(raw).root_node
    except Exception as e:return result('uncertain',lang,'Parser unavailable: '+type(e).__name__)
    if root.has_error:return result('uncertain',lang,'Syntax tree has error/missing nodes; no complete negative classification')
    nodes=list(walk(root));masked=code_mask(root,raw)
    def txt(n):return raw[n.start_byte:n.end_byte].decode('utf-8',errors='replace')
    def body_real(body):
        if body is None:return False
        children=[c for c in body.named_children if 'comment' not in c.type and c.type!='empty_statement']
        if body.type in {'statement_block','block'} and (not children or all(c.type=='expression_statement' and c.named_children and c.named_children[0].type in {'string','string_literal'} for c in children)):return False
        code=raw[body.start_byte:body.end_byte].decode('utf-8',errors='replace')
        stripped=re.sub(r'(?s)/\*.*?\*/|//[^\n]*','',code).strip('{}; \n\r\t')
        return bool(stripped) and not re.fullmatch(r'(?:(?:todo|unimplemented)!\([^)]*\)|throw new (?:NotImplementedException|UnsupportedOperationException)\([^;]*\));?',stripped)
    def ev(node,symbol,kind):return {'symbol':symbol[:160],'line':node.start_point.row+1,'kind':kind}
    plausible=0;empty_cases=0;support=False
    import_text=' '.join(txt(n) for n in nodes if n.type in {'import_statement','import_declaration','using_directive','import_spec','import_or_export'} or n.type=='call_expression' and n.child_by_field_name('function') is not None and txt(n.child_by_field_name('function'))=='require')
    if lang=='dart':
        imported=bool(re.search(r'package:(?:flutter_test|test)/',import_text))
        for n in nodes:
            if n.type!='expression_statement' or not n.named_children:continue
            first=n.named_children[0]
            if first.type!='identifier' or txt(first) not in {'test','testWidgets'}:continue
            plausible+=1
            callbacks=[c for c in walk(n) if c.type=='function_expression']
            if callbacks and imported:
                body=callbacks[0].child_by_field_name('body')
                if body_real(body):return result('automated_test',lang,'Dart/Flutter test runner registers an implemented callback',[ev(first,txt(first),'dart_test_registration')])
                empty_cases+=1
        support=imported
    elif lang in {'javascript','typescript','tsx'}:
        imported=bool(re.search(r'''(?:from\s*|require\s*\(|import\s*)['"](?:vitest|@jest/globals|node:test|bun:test|@playwright/test|mocha|jasmine)''',import_text))
        aliases={'test','it','testWidgets'}
        for m in re.finditer(r'\b(?:test|it)\s+as\s+(\w+)',import_text):aliases.add(m.group(1))
        for m in re.finditer(r'import\s+(\w+)\s+from\s+[\'"]node:test',text):aliases.add(m.group(1))
        for n in nodes:
            if n.type not in {'call_expression','function_expression_invocation'}:continue
            fn=n.child_by_field_name('function')
            if fn is None:continue
            name=txt(fn)
            base=re.split(r'[.(]',name)[0]
            registered=base in aliases or name.startswith(('Deno.test','Bun.test','QUnit.test'))
            if not registered:continue
            plausible+=1
            if re.search(r'\.(skip|todo|fixme)\b',name):continue
            callbacks=[c for c in walk(n) if c.type in {'arrow_function','function_expression','function_literal'}]
            if not callbacks:continue
            body=callbacks[0].child_by_field_name('body')
            if not body_real(body):empty_cases+=1;continue
            body_code=masked.encode('utf-8')[body.start_byte:body.end_byte].decode('utf-8',errors='replace')
            assertions=bool(re.search(r'\b(?:expect|assert|assertEquals|assertStrictEquals|equal|strictEqual|should)\s*[.(]',body_code))
            if imported or name.startswith(('Deno.test','Bun.test','QUnit.test')) or assertions and priority(path)<2:
                return result('automated_test',lang,'Actual test-runner call registers an implemented callback',[ev(n,name,'test_registration')])
        support=bool(re.search(r'\b(?:beforeEach|afterEach|beforeAll|afterAll|jest\.mock|vi\.mock|defineConfig)\b',masked)) or imported
    elif lang=='go':
        testing_import=bool(re.search(r'"testing"',import_text))
        support=testing_import
        for n in nodes:
            if n.type!='function_declaration':continue
            name=n.child_by_field_name('name');params=n.child_by_field_name('parameters');body=n.child_by_field_name('body')
            if name is None or params is None:continue
            symbol=txt(name)
            if symbol.startswith('Example') and path.endswith('_test.go') and body_real(body):
                comments=[txt(c) for c in walk(body) if 'comment' in c.type]
                if any(re.search(r'(?mi)^//\s*(?:Unordered\s+)?Output:',c) for c in comments):
                    return result('automated_test','go','Go executable example with expected output',[ev(n,symbol,'go_example_test')])
            if re.match(r'^(?:Test|Fuzz)(?:$|[^a-z])',symbol) and testing_import:
                plausible+=1
                if not re.search(r'\*\s*testing\.(?:T|F)\b',txt(params)):continue
                if body is not None and re.match(r'\s*\{\s*\w+\.Skip(?:Now|f)?\s*\(',txt(body)):continue
                if body_real(body):return result('automated_test','go','Go test/fuzz entry point with testing parameter and implemented body',[ev(n,symbol,'go_test_entry')])
                empty_cases+=1
    elif lang=='rust':
        for n in nodes:
            if n.type!='function_item':continue
            attrs=[];previous=n.prev_named_sibling
            while previous is not None and previous.type in {'attribute_item','line_comment','block_comment'}:
                if previous.type=='attribute_item':attrs.append(txt(previous))
                previous=previous.prev_named_sibling
            attribute=' '.join(attrs)
            if re.search(r'#\[\s*cfg\s*\(',attribute) and not re.search(r'#\[\s*cfg\s*\(\s*test\s*\)\s*\]',attribute):
                plausible+=1;continue
            if re.search(r'#\[\s*(?:(?:tokio|async_std)::)?test\b|#\[\s*(?:rstest::)?rstest\b',attribute):
                plausible+=1
                if re.search(r'#\[\s*ignore\b',attribute):continue
                body=n.child_by_field_name('body');name=n.child_by_field_name('name')
                if body_real(body):return result('automated_test','rust','Rust test attribute attached to an implemented function',[ev(n,txt(name),'rust_test_function')])
                empty_cases+=1
            elif re.search(r'#\[[^\]]*(?:test_case|test|rstest)',attribute):plausible+=1
        support=bool(re.search(r'#\[\s*cfg\s*\(\s*test\s*\)',text))
    elif lang in {'java','csharp'}:
        framework=bool(re.search(r'\b(?:org\.junit|org\.testng|junit\.framework|Xunit|NUnit|Microsoft\.VisualStudio\.TestTools)\b',import_text))
        for n in nodes:
            if n.type not in {'method_declaration','constructor_declaration'}:continue
            body=n.child_by_field_name('body');name=n.child_by_field_name('name')
            if name is None:continue
            prefix=masked.encode('utf-8')[n.start_byte:(body.start_byte if body else n.end_byte)].decode('utf-8',errors='replace')
            annotation=bool(re.search(r'(?:@|\[)(?:\w+\.)*(?:Test|ParameterizedTest|RepeatedTest|TestFactory|Fact|Theory|TestMethod|DataTestMethod|TestCase|TestCaseSource)\b',prefix))
            junit3=lang=='java' and re.search(r'extends\s+TestCase',text) and txt(name).startswith('test')
            body_code=masked.encode('utf-8')[body.start_byte:body.end_byte].decode('utf-8',errors='replace') if body is not None else ''
            assertion_context=lang=='csharp' and body is not None and (bool(re.search(r'\b(?:Assert|CollectionAssert|StringAssert)\s*\.',body_code)) or bool(re.search(r'AwesomeAssertions|FluentAssertions',import_text) and re.search(r'\.Should\s*\(',body_code)))
            if annotation and re.search(r'\b(?:Skip|Ignore|Disabled)\b',prefix):plausible+=1;continue
            if annotation and not framework and not assertion_context:
                plausible+=1
            if (annotation or junit3) and (framework or assertion_context):
                plausible+=1
                if body_real(body):return result('automated_test',lang,'Recognized framework test annotation/method with implemented body',[ev(n,txt(name),'annotated_test_method')])
                empty_cases+=1
        support=framework
    elif lang=='bash':
        return result('uncertain','bash','Shell script requires semantic assertion/control-flow review; syntax alone is insufficient')
    elif lang=='kotlin':
        if re.search(r'io\.kotest|StringSpec|FunSpec|DescribeSpec',import_text+masked):return result('uncertain',lang,'Kotlin test DSL requires semantic classification')
        framework=bool(re.search(r'kotlin\.test|org\.junit|org\.testng',import_text))
        for n in nodes:
            if n.type!='function_declaration':continue
            code=txt(n)
            if re.search(r'@(?:[\w.]+\.)?Test\b',code):
                plausible+=1
                body=next((c for c in n.named_children if c.type in {'function_body','block'}),None)
                if framework and body_real(body):
                    name=n.child_by_field_name('name') or next((c for c in n.named_children if c.type in {'simple_identifier','identifier'}),None)
                    return result('automated_test',lang,'Kotlin framework test annotation with implemented function',[ev(n,txt(name) if name else '@Test','kotlin_test')])
        support=framework
    else:return result('uncertain',lang,'Language has no sufficiently validated deterministic content rules')
    if plausible:
        if empty_cases==plausible:return result('test_support',lang,'Only empty/unimplemented test registrations detected')
        return result('uncertain',lang,'Potential skipped/dynamic or unconventional test registration needs semantic review')
    if lang=='rust':
        for n in nodes:
            if n.type=='macro_invocation':
                macro=n.child_by_field_name('macro')
                if macro is not None and re.search(r'proptest|quickcheck|test',txt(macro),re.I):return result('uncertain',lang,'Rust macro-generated tests require semantic classification')
            if n.type=='macro_definition' and re.search(r'#\[\s*test\b',masked.encode('utf-8')[n.start_byte:n.end_byte].decode('utf-8',errors='replace')):return result('uncertain',lang,'Rust test-generation macro requires semantic classification')
    if re.search(r'\b(?:eval|exec|include|load_tests)\s*[!(]',masked):return result('uncertain',lang,'Dynamic inclusion or execution prevents a reliable static negative')
    if support:return result('test_support',lang,'Framework/setup/configuration code without implemented registered test cases')
    return result('not_test',lang,'Complete syntax tree contains no recognized test case/registration')


def classify(text,path,complete=True):
    lang=language(path)
    if not complete:return result('uncertain',lang,'Content is truncated/incomplete',complete=False)
    if not isinstance(text,str):return result('uncertain',lang,'Content missing or not text',complete=False)
    if not text.strip():return result('not_test',lang,'Empty file contains no test cases')
    if PurePosixPath(path).name == '.npmrc':
        settings = [line.strip() for line in text.splitlines() if line.strip()]
        if all(re.fullmatch(r'(?:enable-pre-post-scripts|auto-install-peers)\s*=\s*(?:true|false)',
                            line) for line in settings):
            return result('not_test','npmrc','Complete file contains only recognized Boolean package-manager settings')
    if PurePosixPath(path).suffix.lower() in DOCUMENT:return result('not_test',lang,'Documentation, configuration or data file; embedded examples are not executable source test files')
    if len(text.encode('utf-8'))>2_000_000:return result('uncertain',lang,'File exceeds static parser safety limit',complete=False)
    if PurePosixPath(path).name.lower().endswith('.tests.ps1'):
        from powershell_static import standalone_assertions
        lines = standalone_assertions(text)
        if len(lines) >= 2:
            return result('automated_test', 'powershell',
                          'Standalone test script has multiple comparisons that invoke a failure handler exiting nonzero',
                          [{'symbol': 'Write-Fail', 'line': line, 'kind': 'standalone_assertion'}
                           for line in lines])
    if lang=='python':return python_analysis(text,path)
    if lang=='unknown':return result('uncertain',lang,'Unrecognized source language or extensionless executable')
    try:return tree_analysis(text,path,lang)
    except (RecursionError,ValueError):return result('uncertain',lang,'Static analysis resource/syntax failure')
