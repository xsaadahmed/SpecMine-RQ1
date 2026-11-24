"""Offline replay: no network calls and no writes to the midpoint baseline."""
import subprocess
import sys

from hv_common import HERE, OUT, protect_baseline


def main():
    protect_baseline()
    from sample import select_pilot
    from extract import extract
    from review import plan_review,make_form
    from reanalyze import reanalyze
    from design_bounds import design_bounds
    from evaluate_annotations import evaluate
    from validate_pilot import validate
    from report import report
    select_pilot()
    extract()
    plan_review();make_form()
    reanalyze();design_bounds();evaluate()
    result=subprocess.run([sys.executable,"-B","-m","pytest",str(HERE/"tests"),"-q","-o",f"cache_dir={HERE/'.pytest_cache'}",f"--junitxml={OUT/'unit_tests.xml'}"],cwd=HERE,text=True,capture_output=True)
    (OUT / "unit_test_results.txt").write_text(result.stdout+result.stderr,encoding="utf-8")
    print(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError("Historical validation unit tests failed")
    validate()
    report()
    protect_baseline()


if __name__=="__main__":main()
