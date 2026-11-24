# 90-second speaking script

Our question is whether explicit specification practices are associated with automated tests being added. We study associations, not causation.

We built a cohort of 3,186 pull requests across 215 repositories from SpecMine. Each observation is a unique repository and PR number. We link specifications through checked file paths and measure acceptance criteria, edge cases, and explicit testing directives.

The original detector used filenames. The improved detector reads added source files at pinned commits, verifies their hashes, and applies deterministic rules first. Grok handles ambiguous cases. One supported test file establishes a positive, but a negative requires checking every eligible added file.

We have resolved 1,864 PRs, or 58.5 percent. Source inspection changed 44 filename-based labels.

Among resolved PRs, test-addition rates are 66.3 versus 54.3 percent for acceptance criteria, and 58.5 versus 53.6 percent for edge cases. After adjustment, both primary confidence intervals include one, so neither comparison is conclusive.

The biggest limitations are the 1,322 unknown outcomes and specification snapshots that may postdate implementation. Verification also differs by language and tool. Our next steps are broader verification, independent detector validation, and historical-version checks before making stronger claims.

# Likely professor questions

**Why use Grok instead of filenames alone?**
Filenames miss embedded or unusually named tests and can mistake helpers for tests. We inspect source deterministically first; Grok is a fallback for ambiguous languages or conventions, not the default detector.

**How do you ensure reliability?**
Pinned commits, Git-blob/SHA-256 checks, executable-test rules, checked source references, cached decisions and regression tests. Invalid evidence remains unknown. We do not execute downloaded code. These controls establish reproducible source-grounded decisions, not measured accuracy; precision/recall still need independent annotations.

**Why are 1,322 outcomes unknown?**
They are unverified, not negative. Of these, 1,031 are outside the four scaling draws; 291 are selected but unresolved. Reasons include incomplete acquisition, unsupported or ambiguous code, rejected evidence and resource limits. The exact category of every outside-draw PR is not inferred from assignment alone.

**Do better specifications cause better testing?**
No. This is observational, specifications may have changed, and tools, repositories, task complexity and templates can influence both. A test file also does not prove tests ran, passed or improved quality.

**What about historical specification versions?**
Main-cohort features still come from dataset snapshots. The separate pilot verified PR-head specification content for 39 PRs (70 spec observations); 38 currently have resolved content outcomes. PR-head text does not establish pre-implementation timing. Zero pilot PRs were proven to have genuinely pre-implementation specification text. Do not describe main-cohort features as historically verified.

**How does incomplete verification affect validity?**
Completed PRs are not a random subset. Positive cases can finish after one file; negatives need exhaustive coverage. Prioritized acquisition, language support and tool templates affect completion. Repository-clustered intervals address dependence, not missingness or selection bias. Assignment weights alone cannot repair this.

**Does the testing-directive result prove an effect?**
No. It is a secondary English-rule feature. Its nominal adjusted OR is 1.41 [1.02, 1.95], but the three-feature Holm-adjusted p-value is 0.108. Selection, timing, model choice and multiple analyses prevent a confirmatory claim.
