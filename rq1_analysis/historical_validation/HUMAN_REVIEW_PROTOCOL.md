# Prospective independent content annotation

The generated outputs/human_review.csv has blank manual labels. The midpoint's
assistant path labels are not reference annotations and are never copied here.
No precision or recall has yet been evaluated.

Give the reviewer this form, this protocol, and the content-addressed files or
pinned URLs. Withhold review_sample_plan.csv, which contains detector predictions
and sampling strata. Reviewers should not look up those predictions until after
annotation. Content references are pinned; never substitute the current branch.

Suggested labels:

- manual_is_automated_test: 1 if this file defines at least one executable test
  case, BDD scenario, framework-discoverable test, or automated assertion script
  with programmatic pass/fail behavior. Mixed production/test files count as 1
  when such cases actually exist. A test name alone is insufficient.
- 0 for production code without cases, type contracts, specifications,
  configuration, fixtures, mocks, data, documentation, and helper-only modules.
- Leave unresolved cases blank and explain the dependency or evidence needed.
  A shell runner requiring interactive/manual judgment is not automatically 1.
- manual_role: test_case, mixed_production_and_tests, test_support, fixture,
  specification, production, configuration, documentation, other, or uncertain.
- manual_contains_assertions: 0/1 when determinable. Test frameworks can express
  assertions indirectly; absence of the literal word assert is not sufficient.

Use a real reviewer identifier and date; set annotation_origin to
independent_human only when a person independently performed the content review.
Prefer two blinded raters, preserve their separate original forms, and adjudicate
disagreements. Put final 0/1 decisions in adjudicated_label and explain difficult
cases in reviewer_notes. Preserve all original annotation files; score a new
completed/adjudicated copy rather than overwriting the blank template.

Evaluation requires every retrieved case to have an adjudicated label; selective
omission of hard cases would inflate apparent accuracy. The evaluator also
requires an explicit provenance attestation. That gate cannot automatically prove
the annotations' independence or correctness. Weighted metrics concern only the
pilot-file frame, not all SpecMine or all languages. Neither seeing code nor
recognizing assertions proves tests actually ran or passed. Retrieved code must
not be executed as part of annotation.
