import pytest
from detector import classify,eligible,priority


@pytest.mark.parametrize('path,source',[
 ('test_a.py','def test_real():\n    assert 1 == 1\n'),
 ('case.py','import unittest\nclass X(unittest.TestCase):\n def runTest(self):\n  self.assertTrue(True)\n'),
 ('src/embedded.py','import unittest\nclass A(unittest.TestCase):\n def test_x(self):\n  self.assertTrue(True)\n'),
 ('tests/foo.test.ts','import {test,expect} from "vitest"; test("x",()=>{expect(1).toBe(1)});'),
 ('tests/foo.spec.ts','it("x",()=>{expect(1).toBe(1)});'),
 ('app.ts','import {test as check} from "node:test"; check("x",()=>{run()});'),
 ('a_test.go','package p\nimport "testing"\nfunc TestA(t *testing.T){if 1!=1 {t.Fatal("bad")}}'),
 ('src/foo.rs','#[cfg(test)]\nmod tests {#[test]\nfn embedded(){assert_eq!(1,1);}}'),
 ('foo.rs','#[tokio::test]\nasync fn works(){assert!(true);}'),
 ('FooTest.java','import org.junit.Test; class Foo { @Test public void works(){assertEquals(1,1);} }'),
 ('FooTests.cs','using Xunit; class Foo {[Fact] public void Works(){Assert.True(true);}}'),
 ('FooTests.cs','using NUnit.Framework; class Foo {[Test] public void Works(){Assert.IsTrue(true);}}'),
 ('test/foo_test.dart',"import 'package:test/test.dart'; void main(){test('works',(){expect(1,1);});}"),
])
def test_implemented_test_cases(path,source):
    r=classify(source,path)
    assert r['classification']=='automated_test',r
    assert r['has_executable_tests'] is True
    assert all(e['symbol'] in source for e in r['evidence'])


@pytest.mark.parametrize('path,source',[
 ('test_a.py','import pytest\n@pytest.fixture\ndef thing():\n return 1\n'),
 ('tests/test_todo.py','def test_later():\n pass\n'),
 ('tests/a.test.ts','import {test} from "vitest"; test("todo",()=>{});'),
 ('foo.rs','#[test]\nfn todo(){todo!("not implemented");}'),
 ('foo.go','package p\nimport "testing"\nfunc TestA(t *testing.T){}'),
 ('Foo.java','import org.junit.Test; class Foo {@Test public void later(){}}'),
 ('tests/helpers.ts','import {beforeEach} from "vitest"; beforeEach(()=>setup());'),
])
def test_support_and_templates_are_not_positive(path,source):
    r=classify(source,path)
    assert r['has_executable_tests'] is False,r


@pytest.mark.parametrize('path,source',[
 ('test_a.py','def production():\n return "def test_fake(): assert True"\n'),
 ('fake.rs','const S: &str = "#[test] fn x(){assert!(true);}";'),
 ('a.test.ts','const example="test(\'x\',()=>{expect(1).toBe(1)});";'),
 ('Foo.java','import org.junit.Test; class Foo { /* @Test */ public void f(){return;} }'),
 ('specs/spec.md','```python\ndef test_example(): assert True\n```'),
])
def test_comments_strings_and_documents_do_not_register_tests(path,source):
    assert classify(source,path)['has_executable_tests'] is not True


def test_truncation_missing_and_parse_failures_stay_unknown():
    assert classify('def test_yes(): assert True','test_a.py',complete=False)['has_executable_tests'] is None
    assert classify('def test_yes(', 'test_a.py')['has_executable_tests'] is None
    assert classify(None,'test_a.py')['has_executable_tests'] is None


def test_skipped_cases_and_unimplemented_aliases_do_not_become_negatives():
    assert classify('import pytest\n@pytest.mark.skip\ndef test_x(): assert True\n','test_a.py')['has_executable_tests'] is None
    assert classify('package p\nimport t "testing"\nfunc TestA(x *t.T){x.Fatal("bad")}','a_test.go')['has_executable_tests'] is None
    assert classify('import {test} from "vitest"; test("empty",()=>{}); test("x",handler);','a.test.ts')['has_executable_tests'] is None


def test_ranking_and_added_source_eligibility():
    assert priority('tests/a.ts')<priority('src/a.test.ts')<priority('src/a.ts')
    assert eligible('src/foo.rs') and eligible('scripts/check')
    assert not eligible('openspec/specs/test/spec.md') and not eligible('tests/fixture.json')
    assert not eligible('contracts/.gitkeep')


def test_generated_tests_are_uncertain_not_static_negatives():
    assert classify('proptest! { fn works(x in 0..10) { prop_assert!(x < 10); } }','src/lib.rs')['has_executable_tests'] is None
