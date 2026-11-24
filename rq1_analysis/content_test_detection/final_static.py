"""Conservative additions used only by the versioned final offline replay."""
import configparser
import json
import re
from pathlib import PurePosixPath

from detector import code_mask, parser_for, result, walk

VERSION = 'final-static-v1'


def proof(kind, language, reason, symbol, offset, source):
    return result(kind, language, reason, [
        {'symbol': symbol, 'line': source.count('\n', 0, offset) + 1, 'kind': VERSION}
    ], evidence_rule_version=VERSION)


def find_scope(code, start):
    """Return the contents of a structurally balanced brace pair in masked code."""
    depth = 0
    for index in range(start, len(code)):
        if code[index] == '{':
            depth += 1
        elif code[index] == '}':
            depth -= 1
            if depth == 0:
                return code[start + 1:index]
    return ''


def swift_mask(source):
    """Mask the Swift subset used here. Return no proof for unsupported literals."""
    pattern = re.compile(r'//[^\n]*|/\*|#+["/]|"""|"(?:\\[^\n]|[^"\\\n])*"|["/]', re.M)
    chars = list(source)
    start = 0
    while match := pattern.search(source, start):
        token = match.group()
        end = match.end()
        if token == '/*':
            depth = 1
            while depth:
                boundary = re.search(r'/\*|\*/', source[end:])
                if not boundary:
                    return None
                depth += 1 if boundary.group() == '/*' else -1
                end += boundary.end()
        elif token.startswith('//'):
            pass
        elif not token.startswith('"') or token in {'"', '"""'} or '\\(' in token:
            return None
        for index in range(match.start(), end):
            if chars[index] not in '\r\n':
                chars[index] = ' '
        start = end
    return ''.join(chars)


def swift_test(source):
    code = swift_mask(source)
    if not code or re.search(r'(?m)^\s*#\s*(?:if|elseif)\b', code) or '.disabled' in code:
        return None
    if re.search(r'(?m)^\s*import\s+XCTest\s*$', code):
        for case in re.finditer(r'\bclass\s+\w+\s*:\s*XCTestCase\s*\{', code):
            body = find_scope(code, case.end() - 1)
            for method in re.finditer(r'(?m)^\s*(?:override\s+)?func\s+(test\w+)\s*\(\s*\)'
                                      r'\s*(?:async\s*)?(?:throws\s*)?\{', body):
                prefix=body[:method.start(1)]
                if prefix.count('{') != prefix.count('}'):
                    continue
                implementation = find_scope(body, method.end() - 1)
                if 'XCTSkip' not in implementation and re.search(r'\bXCTAssert\w*\s*\(', implementation):
                    return proof('automated_test', 'swift', 'XCTestCase method implements an XCTest assertion',
                                 method[1], case.end() + method.start(1), source)
    if re.search(r'(?m)^\s*import\s+Testing\s*$', code):
        for method in re.finditer(r'(?m)^\s*@Test\s+func\s+(\w+)\s*\(\s*\)'
                                  r'\s*(?:async\s*)?(?:throws\s*)?\{', code):
            if re.search(r'#(?:expect|require)\s*\(', find_scope(code, method.end() - 1)):
                return proof('automated_test', 'swift', 'Swift Testing annotation and implemented check',
                             method[1], method.start(1), source)
    return None


def structured_test(source, language):
    raw = source.encode()
    root = parser_for(language).parse(raw).root_node
    if root.has_error:
        return None
    def text(node):
        return raw[node.start_byte:node.end_byte].decode() if node else ''
    nodes = list(walk(root))
    if language == 'kotlin':
        imports = {text(node).strip() for node in nodes if node.type == 'import_header'}
        if not imports.intersection({'import org.junit.jupiter.api.Test', 'import org.junit.Test',
                                     'import kotlin.test.Test', 'import org.testng.annotations.Test'}):
            return None
        for node in nodes:
            if node.type != 'function_declaration' or not node.parent or node.parent.type != 'class_body':
                continue
            body = next((child for child in node.named_children if child.type == 'function_body'), None)
            modifier = next((child for child in node.named_children if child.type == 'modifiers'), None)
            if not body or not modifier or not re.search(r'(?m)^\s*@Test\s*$', text(modifier)):
                continue
            parent = node
            gated = False
            while parent:
                modifiers = [text(child) for child in parent.named_children if child.type == 'modifiers']
                if any(re.search(r'@(?:[\w.]+\.)?(?:Disabled\w*|Ignore|Enabled\w*|Tag)\b', x)
                       for x in modifiers):
                    gated = True
                parent = parent.parent
            if gated:
                continue
            def direct_check(candidate):
                if candidate.type != 'call_expression' or not re.match(r'(?:assert\w*|expect\w*)\s*\(',text(candidate)):
                    return False
                owner=candidate.parent
                while owner and owner.type not in {'function_declaration','lambda_literal','anonymous_function'}:
                    owner=owner.parent
                return owner==node
            if any(direct_check(n) for n in walk(body)):
                return proof('automated_test','kotlin','Imported test annotation and actual assertion in its method',
                             '@Test',len(raw[:modifier.start_byte].decode()),source)
    elif language == 'scala':
        for node in nodes:
            if node.type != 'class_definition':
                continue
            extends = next((child for child in node.named_children if child.type == 'extends_clause'), None)
            body = next((child for child in node.named_children if child.type == 'template_body'), None)
            if text(extends).strip() != 'extends munit.FunSuite' or not body:
                continue
            for call in body.named_children:
                if call.type != 'call_expression' or not re.match(r'test\(\s*"', text(call)):
                    continue
                contents = next((child for child in call.named_children
                                 if child.type in {'colon_argument','block'}), None)
                if contents and any(n.type=='call_expression' and re.match(r'assert\w*\(',text(n))
                                    for n in walk(contents)):
                    return proof('automated_test','scala','MUnit FunSuite registers a case with an assertion',
                                 'test',len(raw[:call.start_byte].decode()),source)
    return None


SQL_TOKEN = re.compile(r'--[^\n]*|/\*(?![!+])[\s\S]*?\*/|"(?:[^"]|"")*"|'
                       r"'(?:[^']|'')*'|[A-Za-z_]\w*|\d+(?:\.\d+)?|[(),.;\[\]]|\s+")
SQL_ID = r'(?:[A-Za-z_]\w*|"(?:""|[^"])+")'
SQL_LITERAL = r"(?:'(?:(?:'')|[^'])*'|\d+(?:\.\d+)?|NULL|TRUE|FALSE)"
SQL_TYPE = r'(?:BIGINT|INTEGER|INT|SMALLINT|TEXT|VARCHAR|CHAR|BYTEA|DATE|TIMESTAMP|BOOLEAN|UUID|JSONB|DOUBLE PRECISION)'
SIMPLE_SQL = [re.compile(pattern, re.I) for pattern in (
    rf'ALTER TABLE {SQL_ID} (?:ADD COLUMN {SQL_ID} {SQL_TYPE}(?: \( \d+ \))?'
    rf'(?: (?:NOT NULL|NULL|DEFAULT {SQL_LITERAL}))*|DROP COLUMN {SQL_ID})',
    rf'CREATE TYPE {SQL_ID} AS ENUM \( {SQL_LITERAL}(?: , {SQL_LITERAL})* \)',
    rf'DROP TABLE (?:IF EXISTS )?{SQL_ID}',
    rf'CREATE (?:UNIQUE )?INDEX (?:IF NOT EXISTS )?{SQL_ID} ON {SQL_ID} '
    rf'\( {SQL_ID}(?: (?:ASC|DESC))?(?: , {SQL_ID}(?: (?:ASC|DESC))?)* \)'
    rf'(?: WHERE {SQL_ID} IS (?:NOT )?NULL)?',
)]


def schema_only(source):
    # Lexically consume every byte. Comments with executable meaning and
    # dollar-quoted bodies cannot match the grammar and remain unresolved.
    statements, tokens = [], []
    pos = 0
    while pos < len(source):
        match = SQL_TOKEN.match(source,pos)
        if not match:
            return False
        token = match.group()
        pos = match.end()
        if token.isspace() or token.startswith(('--','/*')):
            if token.startswith('/*') and '/*' in token[2:]:
                return False
            continue
        if token == ';':
            if tokens:
                statements.append(' '.join(tokens))
            tokens = []
        else:
            tokens.append(token)
    return not tokens and bool(statements) and all(
        any(rule.fullmatch(stmt) for rule in SIMPLE_SQL) for stmt in statements)


def settings_only(source, name):
    if name in {'.gitmodules', '.import_linter_config'}:
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        try:
            parser.read_string(source)
        except configparser.Error:
            return False
        if parser.defaults() or not parser.sections():
            return False
        if name == '.gitmodules':
            return all(re.fullmatch(r'submodule "[^"\r\n]+"', section)
                       and {'path','url'} <= set(parser[section]) <= {'path','url','branch','shallow'}
                       and all(value and '\n' not in value for value in parser[section].values())
                       for section in parser.sections())
        return parser.sections() == ['importlinter'] and set(parser['importlinter']) <= {
            'root_package','root_packages','include_external_packages'}
    if name == '.prettierrc':
        try:
            options = json.loads(source)
        except ValueError:
            return False
        known = {'semi','singleQuote','trailingComma','printWidth','tabWidth','useTabs','endOfLine',
                 'arrowParens','bracketSpacing','quoteProps','jsxSingleQuote','bracketSameLine'}
        return isinstance(options,dict) and bool(options) and all(
            key in known and type(value) in {str,int,bool} for key,value in options.items())
    return False


SVELTE_TS_NODES = set('program comment import_statement import_clause import_specifier named_imports '
                     'identifier property_identifier type_identifier import_list lexical_declaration variable_declarator '
                     'object_pattern shorthand_property_identifier_pattern type_annotation object_type '
                     'property_signature predefined_type function_declaration formal_parameters '
                     'required_parameter statement_block if_statement return_statement binary_expression '
                     'unary_expression parenthesized_expression ternary_expression call_expression arguments '
                     'member_expression optional_chain array object arrow_function template_string '
                     'template_substitution string string_fragment null number true false expression_statement '
                     'type_predicate type_predicate_annotation'.split())
SVELTE_NODES = set('document script_element start_tag end_tag tag_name raw_text if_statement if_start_expr '
                   'if_end_expr each_statement each_start_expr each_end_expr expression raw_text_expr '
                   'raw_text_each as special_block_keyword element attribute attribute_name attribute_value '
                   'expr_attribute_value quoted_attribute_value text comment'.split())


def display_only_svelte(source):
    """Recognize a limited template with read-only data preparation and display."""
    raw = source.encode()
    root = parser_for('svelte').parse(raw).root_node
    nodes = list(walk(root))
    if root.has_error or any(node.type not in SVELTE_NODES for node in nodes):
        return False
    def text(node):
        return raw[node.start_byte:node.end_byte].decode()
    allowed_tags = {'script','section','div','span','p','a','dl','dt','dd','ul','li','strong','em'}
    allowed_attrs = {'lang','class','href','target','rel','title','id','aria-label'}
    if any((n.type=='tag_name' and text(n) not in allowed_tags)
           or (n.type=='attribute_name' and text(n) not in allowed_attrs) for n in nodes):
        return False
    scripts = [node for node in nodes if node.type=='script_element']
    if len(scripts) != 1 or text(scripts[0].named_children[0]).strip() != '<script lang="ts">':
        return False
    methods = {'filter','join','toFixed','toLocaleString','startsWith'}
    functions = {'$props','$derived','Math.round','formatAmount','countryLabel'}
    for node in nodes:
        if node.type not in {'raw_text','raw_text_expr','raw_text_each'}:
            continue
        snippet = text(node)
        if (node.parent.type=='each_start_expr'
                and re.fullmatch(r'\w+\s*\(\w+\)',snippet.strip())):
            # Keyed #each uses the item's name and a parenthesized key.
            if not re.fullmatch(r'(\w+)\s*\(\1\)',snippet.strip()):
                return False
            continue
        data = (snippet if node.type=='raw_text' else f'({snippet})').encode()
        parsed = parser_for('typescript').parse(data).root_node
        if parsed.has_error:
            return False
        def js(part):
            return data[part.start_byte:part.end_byte].decode()
        for part in walk(parsed):
            if part.type not in SVELTE_TS_NODES:
                return False
            if part.type=='import_statement' and not (re.match(r'import\s+type\b',js(part))
                    or re.fullmatch(r'''import\s*\{\s*countryLabel\s*\}\s*from\s*['"]\$lib/facets['"];?''',js(part))):
                return False
            if part.type=='call_expression':
                callee = part.child_by_field_name('function')
                if not callee:
                    return False
                prop = callee.child_by_field_name('property')
                if js(callee) not in functions and not (prop and js(prop) in methods):
                    return False
    return True


def android_launcher(source):
    lines = [text.strip() for text in source.splitlines() if text.strip()]
    statements = (
        r'\$env:(?:JAVA_HOME|ANDROID_HOME|PATH)\s*=\s*"[^"`\r\n]*"',
        r'Write-Host\s+"[^"`\r\n]*"',
        r'Set-Location\s+"[^"$`\r\n]+"',
        r'java -version',
        r'npx expo run:android',
    )
    return 'npx expo run:android' in lines and all(
        '$(' not in line and any(re.fullmatch(pattern,line) for pattern in statements)
        for line in lines)


def classify_addition(source, path):
    if len(source.encode()) > 2_000_000:
        return None
    file = PurePosixPath(path)
    suffix = file.suffix.lower()
    if settings_only(source,file.name):
        return result('not_test','config','Complete file contains only recognized configuration settings',
                      evidence_rule_version=VERSION)
    if suffix == '.sql' and schema_only(source):
        return result('not_test','sql','Complete SQL consists of bounded schema operations without executable checks',
                      evidence_rule_version=VERSION)
    if suffix == '.ps1' and android_launcher(source):
        return proof('not_test','powershell','Complete script sets launcher environment and starts Expo Android',
                     'npx expo run:android',source.index('npx expo run:android'),source)
    if suffix == '.svelte' and display_only_svelte(source):
        return result('not_test','svelte','Complete component contains only display markup and read-only presentation operations',
                      evidence_rule_version=VERSION)
    if suffix == '.swift':
        return swift_test(source)
    if suffix in {'.kt','.scala'}:
        try:
            return structured_test(source, 'kotlin' if suffix=='.kt' else 'scala')
        except (ValueError, RecursionError):
            return None
    if suffix in {'.cpp','.cc'}:
        raw = source.encode()
        root = parser_for('cpp').parse(raw).root_node
        imports = [raw[n.start_byte:n.end_byte].decode() for n in walk(root)
                   if n.type=='preproc_include']
        if not any(re.fullmatch(r'#\s*include\s*[<"]catch2/[^>"\n]+[>"]\s*', x)
                   for x in imports):
            return None
        code = code_mask(root,raw)
        if re.search(r'(?m)^\s*#\s*(?:if(?:def|ndef)?\b|(?:define|undef)\s+(?:TEST_CASE|REQUIRE|CHECK)\b)',code):
            return None
        for case in re.finditer(r'(?m)^\s*(TEST_CASE)\s*\(\s*(?:,\s*)?\)\s*\{',code):
            if re.search(r'\b(?:REQUIRE|CHECK)(?:_FALSE|_THROWS|_NOTHROW|_THROWS_AS)?\s*\(',
                         find_scope(code,case.end()-1)):
                return proof('automated_test','cpp','Catch2 registration and implemented assertion in its body',
                             'TEST_CASE',case.start(1),code)
    return None
