"""Conservative, auditable path classification; no dependency on is_code."""
import re
from pathlib import PurePosixPath

SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".kts",
    ".go", ".rs", ".rb", ".php", ".cs", ".fs", ".fsx", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
    ".swift", ".m", ".mm", ".scala", ".sc", ".clj", ".cljs", ".ex", ".exs", ".erl", ".hrl",
    ".dart", ".lua", ".r", ".jl", ".pl", ".pm", ".sh", ".bash", ".ps1", ".vue", ".svelte", ".sql",
    ".feature", ".robot", ".bats", ".t", ".groovy", ".vb", ".v", ".zig", ".sol",
}
TEST_DIRS = {"test", "tests", "__tests__", "testing", "e2e", "integration-tests", "integration_tests", "unittests", "unit_tests", "testcases", "spec"}
DATA_DIRS = {"fixture", "fixtures", "__fixtures__", "testdata", "test-data", "test_data", "snapshots", "__snapshots__", "golden", "goldens", "samples", "sample", "mocks", "__mocks__"}
EXAMPLE_DIRS = {"example", "examples"}
VENDOR_DIRS = {"node_modules", "vendor", "third_party", "third-party", ".venv", "venv", "dist", "build", "generated"}
SPEC_DIRS = {"openspec", ".kiro", ".moai", ".specify", ".spec", ".specs", ".claude", ".codex", ".conductor"}


def normalize_path(value):
    """Only remove harmless spelling differences; preserve case and archive paths."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing file path")
    value = value.replace("\\", "/")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ValueError("Expected repository-relative path")
    parts = [x for x in value.split("/") if x and x != "."]
    if ".." in parts:
        raise ValueError("Parent traversal in path")
    return "/".join(parts)


def is_test_change(is_test, change_status, wanted_status):
    """Work with booleans or pandas Series; renamed is never added or modified."""
    return is_test & (change_status == wanted_status)


def classify_test_file(path):
    """Return (is_test, reason, uncertain). This identifies test candidates, not execution."""
    p = PurePosixPath(normalize_path(path))
    dirs = {part.lower() for part in p.parts[:-1]}
    name, low, ext = p.name, p.name.lower(), p.suffix.lower()
    if dirs & VENDOR_DIRS:
        return False, "vendored_or_generated", True
    if ext not in SOURCE_EXTENSIONS:
        return False, "non_executable_extension", False
    if dirs & DATA_DIRS:
        return False, "fixture_sample_or_mock", True
    if low in {"conftest.py", "__init__.py", "setup.py", "tests.py"}:
        if low == "tests.py":
            return True, "python_tests_module", False
        return False, "test_support_module", low != "__init__.py"
    if dirs & SPEC_DIRS or ("specs" in dirs and ext not in {".rb", ".feature", ".robot"}):
        return False, "specification_or_tool_directory", True
    if low in {"test_support.rs", "test_helpers.rs", "test_utils.rs", "test_setup.rs", "test_fixture.rs", "test_fixtures.rs"}:
        return False, "configuration_or_test_support", True
    explicit = (
        (ext == ".py" and (low.startswith("test_") or low.endswith("_test.py")))
        or (ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte"} and bool(re.search(r"\.(test|tests|spec|cy)\.", low)))
        or (ext in {".java", ".kt", ".scala", ".cs", ".vb"} and bool(re.search(r"(Test|Tests|TestCase|Spec|Specs)\.[^.]+$", name)))
        or (ext == ".go" and low.endswith("_test.go"))
        or (ext == ".rs" and (low == "tests.rs" or low.endswith("_tests.rs") or low.startswith("test_")))
        or (ext == ".cs" and low.endswith(".unittests.cs"))
        or (ext in {".rb", ".exs", ".dart", ".rs", ".php", ".swift", ".groovy", ".clj", ".cljs"} and bool(re.search(r"(_test|_spec|Test|Tests|Spec)\.[^.]+$", name)))
        or (ext in {".c", ".cc", ".cpp", ".cxx"} and bool(re.search(r"(^test[_-]|[_-](test|tests)\.)", low)))
        or ext in {".feature", ".robot", ".bats"}
        or (ext == ".ps1" and low.endswith(".tests.ps1"))
    )
    if explicit:
        if dirs & EXAMPLE_DIRS:
            return True, "explicit_test_filename_in_example", True
        return True, "explicit_test_filename", False
    if dirs & EXAMPLE_DIRS:
        return False, "example_source_without_test_filename", True
    if low in {"jest.config.js", "jest.config.ts", "vitest.config.ts", "playwright.config.ts", "cypress.config.ts"} or re.search(r"(^|[._-])(config|setup|helper|helpers|util|utils|support|mock|mocks|fixture|fixtures)([._-]|$)", low):
        return False, "configuration_or_test_support", True
    if dirs & TEST_DIRS:
        return True, "executable_in_test_directory", True
    if ext == ".sh" and (low.startswith("test_") or low.startswith("test-")):
        return True, "shell_test_filename", True
    return False, "no_test_convention", bool(re.search(r"test|spec|check|verify", low))


TEST_TERMS = r"(?:unit|integration|end.to.end|automated|regression|acceptance)\s+tests?"
DIRECTIVE = r"(?:must|shall|should|require[ds]?|add|write|create|implement|include|cover|ensure)"


def testing_requirement(text):
    """Secondary English-only signal: directive and test phrase within one prose line.

    Ignore fenced code, HTML comments, and explicit negations. No bare 'testing'
    heading or test mention suffices. Return a matched-rule count, no raw prose.
    """
    if not isinstance(text, str):
        return None, 0
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.S)
    matches = 0
    for line in text.splitlines():
        if re.search(r"\b(no|not|without|unnecessary|optional|out of scope)\b", line, re.I):
            continue
        if re.search(rf"\b{DIRECTIVE}\b.{{0,100}}\b{TEST_TERMS}\b|\b{TEST_TERMS}\b.{{0,100}}\b{DIRECTIVE}\b", line, re.I):
            matches += 1
    return int(matches > 0), matches
