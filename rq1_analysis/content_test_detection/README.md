# Content-based automated test detection

This extension preserves all SpecMine source data, the midpoint analysis, the
historical pilot, its acquisition cache, and existing reviews. Start with
[CONTENT_DETECTION_SUMMARY.md](CONTENT_DETECTION_SUMMARY.md) and the
[full executed report](CONTENT_DETECTION_REPORT.md). prior_work_manifest.json
fingerprints 684 pre-existing substantive files. This directory owns every new
research write. Do not run old project runners to regenerate their frozen results.

## Executed scope

The cached 56-file evaluation and 40-PR pilot were executed, followed by a frozen
additional 24-PR main-cohort acquisition subset. All 3,186 PR identities appear
in the output queue, with unknowns for uninspected/unresolved observations.
Actual xAI calls and cost were zero because XAI_API_KEY was unavailable.
The live provider integration remains unvalidated; mock SDK tests do not count
as a live smoke batch. Current official API documentation and the installed SDK
were checked; see [XAI_DOCUMENTATION.md](XAI_DOCUMENTATION.md).

## Reproduce the no-cost run

From the original repository root, use the delivered separate environment:

```powershell
rq1_analysis/content_test_detection/.venv/Scripts/python -B rq1_analysis/content_test_detection/run.py --dry-run
```

This performs no paid requests and no new GitHub requests. It verifies caches,
classifies contents, resumes PR searches, regenerates only extension outputs,
runs tests, and verifies prior-work hashes. Existing GitHub/model results and
deterministic classifications are reused. The process lock prevents concurrent
paid runs from racing the budget or identical-content cache.

To create a fresh environment, install requirements.txt in this extension's
.venv. The executed environment used --system-site-packages to reuse installed
scientific libraries; a fully isolated installation was not separately executed.
statsmodels is optional for the current sparse run, where regression is withheld.

```powershell
python -m venv --system-site-packages rq1_analysis/content_test_detection/.venv
rq1_analysis/content_test_detection/.venv/Scripts/python -m pip install -r rq1_analysis/content_test_detection/requirements.txt
```

On Linux/macOS use .venv/bin/python. Offline reproduction requires the original
data/, midpoint outputs, historical cache/content, this extension's cache/, and
.parser_cache/ grammars. Copy these privately when moving the project. Raw source
and predictions may be license-sensitive and are ignored by Git by default.
Parser grammars come from the installed tree-sitter package and are downloaded
to this extension on first use; retrieved PR source is never executed or imported.

## Secure xAI setup and first real batch

Run this in a local PowerShell terminal. The key is entered into a secure terminal
prompt, not pasted into chat or stored in a source/.env file. The environment
variable is available to Python processes launched by that terminal.

```powershell
$grokSecret = Read-Host 'xAI API key' -AsSecureString
$env:XAI_API_KEY = [System.Net.NetworkCredential]::new('', $grokSecret).Password
rq1_analysis/content_test_detection/.venv/Scripts/python -B rq1_analysis/content_test_detection/run.py --grok --max-grok-requests 10 --max-spend 3
```

Do not print the variable. No key value is written to logs, caches, or Git.
Without XAI_API_KEY, --grok records unresolved cases and never invokes the SDK.
Default execution remains a dry run even when a key exists, unless --grok is used.
No alternative provider/model/reasoning setting is substituted.

The first batch is capped at ten total SDK request attempts, including retries.
Review outputs/grok_smoke_validation.json, api_usage_report.json, and cached
predictions. Then validate actual responses and accounting locally:

```powershell
rq1_analysis/content_test_detection/.venv/Scripts/python -B rq1_analysis/content_test_detection/run.py --validate-smoke
```

Only a passed live smoke gate permits a request ceiling above ten. The gate stays
closed when there were no live responses, malformed responses, failed evidence,
failed/reserved attempts, or unreconciled provider costs. After a successful gate:

```powershell
rq1_analysis/content_test_detection/.venv/Scripts/python -B rq1_analysis/content_test_detection/run.py --grok --max-grok-requests 50 --max-spend 3
```

Request and dollar limits are cumulative across resumes. An initial-evaluation
limit above $3 is rejected; changing it requires a separately authorized protocol.
The ledger reserves a conservative token-cost bound before dispatch and reconciles
actual cost_in_usd_ticks/1e10 when supplied. Failed/unknown costs retain their
reservation. A $0.06 minimum reserve also covers the documented rejection fee.
Transport retries are disabled in the SDK; this code performs at most three
counted attempts for rate-limit/unavailable responses. Auth/schema/unsupported
evidence failures are not silently retried. Successful and failed content decisions
are cached, so a normal resume does not repeatedly charge identical content.

## Classification and search

Only added files in a PR's complete net diff can supply the primary positive.
Modified and removed review files are evaluated separately. Content reads use
full pinned head SHAs and verify Git blob/SHA-256 hashes. Reusing old responses
does not refresh or alter the historical pilot. A changed live net diff is flagged
unknown relative to the frozen study, rather than silently defining a new outcome.

Candidate ordering is test directories, then test-like filenames, then all other
eligible executable sources. Examples and fixtures are not automatically positive;
their contents matter. Ordinary Rust source can contain #[test] modules and is
searched when added. No arbitrary pre-existing repository files are searched.
Markdown/specification documents, data/configuration, binary assets, and known
repository markers such as .gitkeep are not executable source candidates.
Extensionless executable candidates and uncommon source extensions are retained;
unsupported cases stay uncertain. Source eligibility is an explicit finite rule
set and can miss unrecognized file types; language coverage is a validity limit.

The Python detector uses ast; other supported languages use tree-sitter syntax
trees. Comments and stringified examples do not register cases. Rules recognize
implemented Python tests/assertions, Jest/Vitest/Node/Playwright-style callback
registrations, Go testing entries/examples, Rust test attributes/embedded modules,
JUnit/TestNG methods, xUnit/NUnit/MSTest methods, and Dart test callbacks. Kotlin
framework tests are supported conservatively. Fixtures/setup without cases are
test_support; empty templates are not positives. Dynamic/macro-generated tests,
parser failures, shell semantics, unusual frameworks, unsupported languages, and
unresolved skipped-only code can require Grok. This is static source evidence,
not proof of discovery, execution, passing assertions, or software quality.

One positive stops the search and cancels remaining content requests for that PR.
A negative requires a complete compatible file list and a resolved negative/support
classification for every eligible added file. Unknown retrieval/classification
never becomes zero. Missing higher-ranked content can be deferred while lower-
ranked cached files are examined; a positive there avoids further downloads.
Counts describe unique PR/file examinations in a search, including cached decisions,
not repeated parser CPU calls. File evaluation and PR-search counts overlap.

Grok receives language, path, and sanitized actual source as untrusted data. No
tools or repository execution are enabled. Pydantic/JSON Schema constrains output;
application checks verify class/boolean consistency, review flags, exact citations,
completion status, and conflicts with strong static evidence. Keys, credential
URLs, private keys, and sensitive contexts are blocked; obvious emails/personal
comment metadata are redacted. Sanitization is conservative and cannot certify
all sensitive information has been found. Context loss keeps a case unresolved.

Complete files up to 48 KB are preferred. Larger files can use whole AST declaration
and import ranges; if those cannot preserve relevant context they stay unknown.
Excerpt-only negatives/support conclusions are prohibited. Predictions are keyed
by original content hash, model, reasoning setting, and prompt version, permitting
reuse across identical files. Model predictions are not independent reference truth.

## GitHub acquisition, scaling, and resumption

outputs/resource_estimate.json records source-file counts, worst-case request
bounds, token/cost scenarios, and caps before acquisition. The executed run used
the connected GitHub plugin through connector_fetch.js, eight frontier requests
per invocation with at most two concurrent reads and pauses. The default total
new-read cap is 200; all previous historical reads are reused. API errors are
cached explicitly. Source requests are generated only for unresolved PR frontiers,
so confirmed PRs cannot trigger later downloads.

An optional portable GET-only Python client is also implemented. It was not used
for this run's network acquisition. Supply GITHUB_TOKEN through the environment
if needed; its value is never logged. It respects low quota/rate limits and the
cumulative request cap. To activate another deterministic batch and fetch within
remaining capacity:

```powershell
rq1_analysis/content_test_detection/.venv/Scripts/python -B rq1_analysis/content_test_detection/run.py --stage main --extend-main 24 --fetch-github --github-limit 200 --dry-run
rq1_analysis/content_test_detection/.venv/Scripts/python -B rq1_analysis/content_test_detection/run.py --dry-run
```

--dry-run disables paid xAI calls; --fetch-github explicitly permits free GitHub
reads. Default runs never perform new network acquisition. Each added batch is
saved separately; the original draw is preserved. main_resumable_queue.csv keeps
all unresolved PRs, including those not yet activated. Persistent per-PR checkpoints,
immutable GitHub/model responses, and classification caches allow restarts.
Do not delete the budget ledger or failed-prediction cache to bypass limits.

For `full_cohort.py` and `overnight.py`, set `--max-grok-spend 7` for a
$7 cumulative limit, `--max-grok-requests 1000` for a 1,000-attempt
lifetime limit, and `--max-new-model-calls 100` for up to 100 new
attempts per invocation of the cohort runner. Overnight applies that last
limit per child pass. Charges and reservations in the existing ledger count
toward the cumulative limits. Retries count as attempts. Omitting the flags
uses the previous defaults of $3, 100 lifetime attempts, and 10 per run.

The overnight supervisor visits every existing batch for cached and deterministic
work before rotating through model passes. Each model pass uses cached GitHub
evidence and is bounded by `--max-new-model-calls`. With
`--prioritize-low-cost`, the runner puts cache-ready cases and PRs with fewer
remaining model-dependent files first. The supervisor reports why paid work
stopped and carries both circuits forward without requesting a reset.

The opt-in revised evidence request uses a separate quality window. Run
`evidence_trial.py` offline to check the three pinned fixtures, or add
`--live` for one budgeted attempt per fixture. The trial stops on the
first unvalidated or unexpected outcome. Trial caches stay isolated
until all three complete PR outcomes match the reviewed expectations.
`overnight.py --evidence-v5` admits the verified decisions, then uses
the revised request during paid passes over PRs with no independent
evidence blockers. The legacy window remains available for audit.

For a supervised restart after quality fallback, pass
`--rearm-model-quality` to a live `full_cohort.py` invocation. This
creates one persistent trial window per prompt and validator version and
preserves the original window. Subsequent live invocations reuse the trial
window. Repeating the flag cannot clear its history or reopen a tripped
trial. Start with `--max-new-model-calls 10` to bound the first trial.
The existing rolling breaker, validation, cache reuse, and failure handling
apply during the trial.

If the two most recent attempts are distinct requests that both returned
`INVALID_ARGUMENT` under the current model and prompt, the cohort resolver
blocks new Grok dispatches across restarts. The run can still reuse cached
decisions and inspect source deterministically. The progress report records
`grok_transport_blocked_invalid_argument`. Review the provider rejection
before changing the request format. New rejection records retain allowlisted
field names mentioned by the provider alongside the gRPC status.

After verifying corrected credentials, use `--rearm-model-transport` with
`--live --max-new-model-calls 2`. The two-attempt cap includes SDK transport
retries. Probe attempts are marked in the existing ledger, and a probe that
ends without provider usage keeps automatic dispatch blocked on restart. Old
rejected inputs stay cached, and the current model-quality window still applies.

## Outputs and interpretation

- file_classification_results.csv: all 56 cached review cases, old/static/Grok/
  hybrid decisions, status, code evidence, hashes, and method. Grok decisions are
  absent when no real request ran.
- pilot_pr_outcomes.csv / main_pr_outcomes.csv: original test_added and new
  test_added_content_verified (1/0/blank unknown), detection method/evidence,
  pinned commits, confirmed paths, eligible/inspected counts, and completeness.
- *_inspection_audit.csv: individual source decisions/provenance. *_pr_summary.json
  records totals, means, medians, unknowns, disagreements, and early-exit savings.
- main_acquisition_subset.csv / main_batches/: deterministic active draws.
  main_resumable_queue.csv and *_github_frontier.json retain remaining work.
- grok_output_schema.json, grok_dry_run_plan.json, api_usage_report.json,
  api_ledger.json when calls occur, and grok_smoke_validation.json: provider contract,
  preflight estimates, actual usage/cost, durable reservations, and live gate.
- tables/: file/PR disagreements, tool/language/repository coverage, and separate
  historical-head versus snapshot-specification RQ1 rates. Unknowns are explicit.
- statistical_analysis_status.json: reasons for withholding regression. Wilson
  reference intervals describe selected verified subsets only; missingness bounds
  show how broad overall rates remain if unknown outcomes are either 0 or 1.
- validation_results.json, unit_test_results.txt, unit_tests.xml: executed tests
  and source/completeness/budget/prior-work integrity evidence.
- CONTENT_DETECTION_REPORT.md / CONTENT_DETECTION_SUMMARY.md: detailed and concise
  executed findings; figures/ includes verification coverage.

The main verification subset is small and deliberately selected; the historical
pilot was stratified on the original outcome. Neither is a representative outcome
sample for naive association testing. The original snapshot features remain
unverified for PR-time specification versions outside the historical cohort.
Regression guards require adequate N, repository clusters, events and outcome
coverage. Even a future model remains associational and may retain selection,
template, language and measurement confounding. Accuracy/precision/recall remain
unavailable until independent trustworthy reference annotations exist.
