import pytest

from classifiers import classify_test_file, normalize_path, testing_requirement as detect_testing_requirement, is_test_change


@pytest.mark.parametrize("path", [
    "test_parser.py", "pkg/parser_test.py", "tests/integration/cache.py",
    "app/foo.test.js", "app/foo.spec.ts", "__tests__/widget.tsx",
    "src/test/java/Example.java", "src/ExampleTest.java", "pkg/main_test.go",
    "spec/models/user_spec.rb", "test/user_test.exs", "test/login_test.dart",
    "tests/test_queue.cpp", "tests/PolicyTests.cs", "features/login.feature",
    "test/smoke.bats", "tests/acceptance.robot", "scripts/Foo.Tests.ps1",
    "crates/ui/src/tests.rs", "src/utils_tests.rs", "src/Window.unittests.cs",
])
def test_common_test_conventions(path):
    assert classify_test_file(path)[0]


@pytest.mark.parametrize("path", [
    "specs/001-tests/spec.md", "openspec/specs/login/spec.md", "tests/README.md",
    "tests/fixtures/test_user.py", "samples/test_api.py", "tests/__snapshots__/view.snap",
    "tests/data.csv", "tests/conftest.py", "tests/__init__.py", "tests/helpers.ts",
    "src/config.ts", "src/contest.py", "src/testing-guide.md", "vendor/pkg/test_foo.py",
    "tests/jest.config.js", "specs/001-api/contracts/api.ts", "node_modules/a/foo.test.js",
    "examples/demo.py",
    "crates/ui/src/test_support.rs", "tests/test_helpers.rs",
])
def test_exclusions(path):
    assert not classify_test_file(path)[0]


def test_uncertainty_is_explicit():
    assert classify_test_file("tests/api.py")[2]
    assert not classify_test_file("tests/test_api.py")[2]
    assert classify_test_file("tests/fixtures/test_api.py")[2]
    assert classify_test_file("examples/demo/tests/test_api.py")[0]
    assert classify_test_file("examples/demo/tests/test_api.py")[2]


def test_paths_preserve_history_and_case():
    assert normalize_path("./openspec//changes/archive/a/spec.md") == "openspec/changes/archive/a/spec.md"
    assert normalize_path("src\\Foo.java") == "src/Foo.java"
    assert normalize_path("src/Foo.java") != normalize_path("src/foo.java")
    for invalid in ["../a", "/a", "C:\\x", None, ""]:
        with pytest.raises(ValueError): normalize_path(invalid)


@pytest.mark.parametrize("text, expected", [
    ("We must add unit tests for malformed input.", 1),
    ("Integration tests shall cover failures.", 1),
    ("Write automated tests for the new endpoints.", 1),
    ("## Testing\nThe endpoint is described here.", 0),
    ("No unit tests are required.", 0),
    ("Unit tests are optional.", 0),
    ("```\nMust add unit tests\n```", 0),
    ("<!-- Write unit tests -->", 0),
    (None, None),
])
def test_testing_directive(text, expected):
    assert detect_testing_requirement(text)[0] == expected


@pytest.mark.parametrize("status", ["added", "modified", "removed", "renamed"])
def test_change_status_is_not_conflated(status):
    assert is_test_change(True, status, "added") == (status == "added")
    assert is_test_change(True, status, "modified") == (status == "modified")
    assert not is_test_change(False, status, "added")
