"""Resumable extension runner. Default is offline with a no-cost Grok dry run."""
import argparse
import importlib.metadata
import json
import subprocess
import sys

import portalocker

from common import HERE,OUT,protect_prior,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['all','files','pilot','main','report'],default='all')
    parser.add_argument('--grok',action='store_true',help='Allow paid calls only if the key, smoke/request gate and $3 budget permit')
    parser.add_argument('--dry-run',action='store_true',help='Never call xAI, even when --grok is supplied')
    parser.add_argument('--max-grok-requests',type=int,default=10,help='Cumulative attempts including retries')
    parser.add_argument('--max-spend',type=float,default=3.0)
    parser.add_argument('--fetch-github',action='store_true',help='Portable REST acquisition of active frontiers, optional GITHUB_TOKEN')
    parser.add_argument('--github-limit',type=int,default=200,help='Cumulative new request ceiling; historical reads are reused')
    parser.add_argument('--extend-main',type=int,default=0,help='Activate another reproducible acquisition batch')
    parser.add_argument('--validate-smoke',action='store_true',help='Validate actual smoke responses/accounting before raising cumulative request cap')
    args=parser.parse_args()
    from cohort_overlay import reference_trial_required
    if args.grok and not args.dry_run and reference_trial_required(OUT/'full_cohort'):
        parser.error('The historical paid runner is closed. See independent_review.py.')
    protect_prior()
    from acquire import resource_estimate
    from grok import Classification,GrokResolver
    from pipeline import evaluate_files,extend_main_subset,process_prs,save_grok_plan
    from smoke import validate_smoke
    write_json(OUT/'grok_output_schema.json',Classification.model_json_schema())
    write_json(OUT/'environment.json',{'python':sys.version.split()[0],'packages':{p:importlib.metadata.version(p) for p in ['pandas','pyarrow','tree-sitter','tree-sitter-language-pack','xai-sdk','pydantic','pytest','portalocker']}})
    resource_estimate()
    if args.validate_smoke:
        print(json.dumps(validate_smoke(),indent=2));return
    if args.extend_main:print('Activated additional main PRs:',extend_main_subset(args.extend_main))
    resolver=GrokResolver(dry_run=not args.grok or args.dry_run,max_spend=args.max_spend,max_requests=args.max_grok_requests)
    if args.stage in ['all','files']:evaluate_files(resolver)
    if args.stage in ['all','pilot','main']:
        scopes=['pilot','main'] if args.stage=='all' else [args.stage]
        for scope in scopes:
            if args.fetch_github:
                from fetch_github import fetch
                print(fetch(scope,args.github_limit))
            d,_=process_prs(scope,resolver)
            print(scope,d.test_added_content_verified.value_counts(dropna=False).to_dict())
    save_grok_plan(resolver)
    if args.stage in ['all','report']:
        from analyze import analyze
        from validate import validate
        from report import report
        analyze()
        result=subprocess.run([sys.executable,'-B','-m','pytest',str(HERE/'tests'),'-q','-o',f'cache_dir={HERE/".pytest_cache"}',f'--junitxml={OUT/"unit_tests.xml"}'],cwd=HERE,text=True,capture_output=True)
        (OUT/'unit_test_results.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        print(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Content-detection unit tests failed')
        validate();report()
    protect_prior()


if __name__=='__main__':
    # A process lock prevents concurrent paid runs from racing the budget ledger
    # or charging twice while the same content prediction is being written.
    with portalocker.Lock(str(HERE/'.run.lock'),timeout=.1):main()
