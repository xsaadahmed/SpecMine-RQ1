# RQ1 historical-validation extension

Start with [PILOT_SUMMARY.md](PILOT_SUMMARY.md), then
[PILOT_REPORT.md](PILOT_REPORT.md). This directory extends the November 5 midpoint
baseline without editing it. Read the initial [feasibility assessment](FEASIBILITY.md)
and [human annotation protocol](HUMAN_REVIEW_PROTOCOL.md).

## Preservation and scope

baseline_manifest.json freezes 103 existing project/input files. The original
data, midpoint source, reports, outputs, and reviews are unchanged. The verified
midpoint_baseline_nov05.zip additionally archives the original project files,
without duplicating raw datasets. Do not run the old midpoint runner in place
to regenerate its historical outputs; restore the archive into a separate copy
if you need to reproduce that baseline afresh.

Only this directory receives writes. Raw GitHub contents and sanitized API
responses are cached locally and ignored by Git. Source text/code is not executed.
Honor each source repository's license when sharing cached content. Reports and
exported research tables use identifiers, hashes, features, and aggregates,
without API author profiles, email addresses, signatures, or raw prose.

The executed pilot used the **connected GitHub plugin**. No full SpecMine corpus
was downloaded. API-recorded heads were captured at retrieval and pinned; a head
is not a PR-creation version or proof of pre-implementation text.

## Offline reproduction of the executed pilot

Use the existing project environment from the repository root:

```powershell
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/run.py
```

This command makes no network calls. It reuses immutable cached API responses,
checks pinned blobs, re-extracts features, regenerates the separate pilot
statistics/reports, runs extension tests, validates the blank annotation form,
and verifies the original baseline/archive. It preserves any existing human form.
Complete annotations should be saved as a new file, not entered into the blank
template. All baseline scripts remain unexecuted.

Offline reproduction requires the local cache/ directory. Keep it and the local
outputs/content/ directory when moving this project privately; they are ignored
by Git to avoid redistributing source artifacts by default. The immutable
outputs/acquisition_cache_manifest.json fingerprints every acquired response.
A public checkout without those caches cannot guarantee identical reacquisition
because repositories, PR records, and access can change. Pinned head/anchor SHAs,
paths, blob hashes, and content references remain in the exported evidence tables.

Python 3.14.2 and the frozen midpoint environment were used. The extension adds
no dependencies for offline replay. requirements.txt references the midpoint
requirements and adds requests for the optional portable acquisition client.
An isolated environment and the optional REST transport were not separately
executed in this session; the cached connector acquisition and offline replay
were executed and tested. On Unix, use .venv/bin/python instead of Scripts/python.

Separate stages, after their prerequisites exist:

```powershell
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/sample.py
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/extract.py
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/review.py plan
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/review.py form
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/reanalyze.py
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/design_bounds.py
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/validate_pilot.py
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/report.py
```

## Acquisition and API limits

plan.py builds bounded queues for metadata, paginated files, paginated commits,
commit details, head_content, earlier_content, and review_content. Successful
and failed requests are immutable, keyed by canonical request arguments. A 404
does not become an absent feature. Historical failures never use snapshot text.
The sample is frozen before availability is inspected and failed PRs are not
replaced. New acquisition attempts should use a separately versioned run/copy,
preserving this pilot's caches, results, and forms.

connector_fetch.js contains the actual acquisition orchestration. It is run
inside Codex's functions.exec environment with a `stage` string and a tools
object, using the GitHub connector. It is not a standalone Node program.
The authored source can be evaluated in an async wrapper as follows:

```javascript
const stage = "head_content";
// source is the local connector_fetch.js text, not downloaded content.
await eval("(async()=>{" + source + "})()");
```

The orchestrator processes at most eight requests per invocation, two concurrent
reads at a time, with pauses. It stops on rate-limit errors without caching those
as permanent missing content. No rate-limit events occurred in the executed pilot.
The connector does not expose remaining-quota headers. Its response normalizer
retains only needed metadata, paths/statuses/blob hashes, commit ancestry/dates,
and requested file bytes, dropping API personal/contact fields. The JS file's
workspace path is explicit; update it when working in another checkout.

For portable reacquisition in a fresh versioned copy, rest_fetch.py provides
equivalent GET-only requests and response sanitization. Supply GITHUB_TOKEN in
the environment if needed; it is never printed or saved. Unauthenticated API
quotas will generally be insufficient for a complete fresh pilot.

```powershell
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/rest_fetch.py metadata
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/rest_fetch.py files
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/rest_fetch.py commits
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/rest_fetch.py anchor
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/rest_fetch.py head_content
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/rest_fetch.py earlier_content
```

Run review.py plan before acquiring review_content. Repeat a stage only if
plan.py still lists pending requests. The REST client limits each invocation to
80 requests, makes at most one request per second, stops at low remaining quota
or rate-limit responses, and never overwrites cached errors. Network transport
errors stop execution for a resumable run. API caps and incomplete pagination
prevent a completeness/precedence claim. The earlier history scan has a
12-commit prefix budget per PR; one case reaches that limit in this pilot.

## Research design and interpretation

The PR pilot is a 40-case probability sample from 3,070 closed two-tool PRs in
the midpoint cohort. Twenty cases per tool include eight acceptance-positive
cases, deliberately oversampling rare exposures. Within those groups, edge-case
and test-addition cells receive balanced quotas subject to capacity. Selection
uses a fixed hash ordering; weights N_h/n_h are retained. Sampling Protocol and
pilot_sampling_strata.csv document exact probabilities. No population inference
is justified from raw pilot rates because outcome is a selection stratum.

All active specs must be independently retrieved for a complete historical PR.
Paths are exact unless the API explicitly supplies previous_filename. Net diff
path/status equality with the baseline validates reuse of the frozen path-based
test outcome, which remains unvalidated against human content labels.

features.py defines English structural acceptance/edge heading rules, ignoring
comments/code fences. It reuses the frozen testing-directive rule. Original
extractor code is unavailable; supplied-label versus new-rule snapshot agreement
is a **definition check**. New-rule snapshot versus new-rule head agreement is
a **version check**. Do not conflate them. Word counts sum across active specs;
binary PR predictors use any-presence only after complete historical retrieval.

An earlier anchor is the parent of the first observed executable source/test
change after a checked linear PR-history prefix. Tests/fixture code count as
implementation. Unsupported language/config changes and work outside the history
can be missed; genuinely pre-implementation content is never claimed. The
current PR base SHA alone is not the anchor. Missing earlier text stays unknown.

Reanalysis reports both original IPW and a named response-calibrated sensitivity.
The latter assumes response within the original stratum is ignorable. Neither
fixes curated corpus selection, weak exposure overlap, feature-rule uncertainty,
or detector errors. Primary finite-frame uncertainty uses exact hypergeometric
count intervals per sampling stratum, simultaneous Bonferroni coverage over 64
domain/exposure counts, and conservative propagation to rates/differences. The
target is the protocol-retrievable/compatible domain in the fixed curated frame;
the failed PR belongs to neither exposure group, without imputing its feature.
Validity relies on pseudorandom within-stratum sampling and a stable domain state,
not on independent repository outcomes. Bounds are very wide with 1–3 draws per
stratum. Separate bootstrap intervals resample repositories with fixed weights;
they illustrate composition uncertainty, not survey-design confidence. No logistic regression or naive
independence-test p-values are produced from this sparse outcome-stratified pilot.
The largest weighted acceptance shift is already present under definition drift;
it must not be called a historical-version effect. See statistical_limits.json.

## Files and outputs

- hv_common.py: isolated paths, immutable cache identity, baseline checks,
  read-only import of the frozen path/directive classifier.
- sample.py: frozen stratified selection and inclusion probabilities.
- plan.py: pagination/completeness, exact-path resolution, source-change history
  scan, and acquisition request queues.
- connector_fetch.js / rest_fetch.py: connector acquisition and portable REST
  alternative. Only the connector transport was used for this pilot.
- features.py / extract.py: versioned rules, Git/SHA-256 checks, paired features,
  head and earlier cohorts; missing historical features remain null.
- review.py / evaluate_annotations.py: separate blinded blank review form,
  pinned contents, design weights, and human-provenance evaluation gate.
- reanalyze.py / design_bounds.py / report.py: paired agreement, tool-specific
  weighted descriptions, conservative exact finite-frame confidence bounds,
  sensitivity tables, plots, and reports.
- validate_pilot.py / tests/: baseline/archive and evidence invariants; tests
  cover heading rules, no snapshot fallback, blob integrity, ancestry, truncation,
  and refusal of assistant reference labels.

Key outputs:

- outputs/pilot_sample.csv: frozen 40-case selection, original selection features,
  strata and design weights; not a historical analysis table.
- outputs/historical_spec_files.csv: every planned active path, resolution status,
  hashes, pinned refs, supplied snapshot/new snapshot/new head features, and
  version/definition mismatch flags.
- outputs/earlier_spec_files.csv and anchor_audit.json: earlier retrieval and
  ancestry evidence, inaccessible paths, resource/linearity blockers.
- outputs/pilot_observations.csv: all 40 PRs, including exclusions and explicit
  missing historical predictors.
- outputs/historical_head_analysis_cohort.csv: 39 complete verified head PRs.
  Use `historical_head_has_*` predictors; original supplied and same-rule snapshot
  predictors are explicitly prefixed. No unprefixed historical/snapshot mix.
- outputs/earlier_complete_analysis_cohort.csv: 11 PRs with complete earlier text.
  Use `earlier_has_*`; genuine_preimplementation_proven remains false.
- outputs/human_review.csv: 56 blank human-review candidates with verified
  commit/blob/SHA-256/content references. No detector predictions in this form.
- outputs/review_sample_plan.csv: predictions, uncertainty strata and file-sample
  weights; keep this separate from blinded annotators.
- outputs/tables/: feature agreement, byte identity, changed-label cases, weighted
  testing rates/contrasts, response weights, earlier/head comparisons, and clearly
  separated full-frame snapshot template context.
- outputs/figures/: historical tool-specific plot.
- outputs/content/: content-addressed UTF-8 source/spec files, local/ignored.
- cache/responses/: immutable sanitized API responses, local/ignored.
- outputs/validation_results.json, unit_test_results.txt, unit_tests.xml:
  actual integrity and unit-test evidence.

## After independent annotation

Do not fill labels using an AI assistant and call them human validated. Follow
HUMAN_REVIEW_PROTOCOL.md; preserve each rater's form and adjudicate independently.
Save a completed form under a new filename, then attest to its real provenance:

```powershell
rq1_analysis/.venv/Scripts/python -B rq1_analysis/historical_validation/evaluate_annotations.py --annotations PATH_TO_COMPLETED_COPY.csv --human-reference-attested
```

Until that exists, precision and recall remain null. Attestation cannot itself
prove independence. Any later metrics need file-sampling weights and apply only
to the pilot's changed-file frame; no full-corpus or test-quality conclusion.
