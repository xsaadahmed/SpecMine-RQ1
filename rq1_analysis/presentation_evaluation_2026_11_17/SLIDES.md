# Slide 1 — RQ1: Study Design

**Are explicit specification practices associated with automated tests being added?**

- **Data:** 3,186 PRs, 215 repositories; SpecMine sample.
- **Specifications:** acceptance criteria, edge cases, testing directives*.
- **Matching:** checked repository/path links; one observation per repository + PR number.
- **Outcome:** an added source file contains automated tests at a pinned commit; deterministic analysis first, Grok for ambiguity.
- **Evaluation:** compare rates and repository-aware intervals; exploratory adjustment for tool, language and specification characteristics.

*Snapshot features; testing directives use a secondary English text rule. Unknown outcomes stay unknown.*

---

# Slide 2 — RQ1: Evaluation and Progress

**1,864 / 3,186 PRs resolved (58.5%): 1,023 positive, 841 negative**

| Specification feature | Test added: present / absent |
|---|---:|
| Acceptance criteria | 66.3% / 54.3% |
| Edge cases | 58.5% / 53.6% |
| Testing directive* | 65.3% / 53.7% |

- Source inspection changed **44 filename labels**: 33 negatives → positives; 11 positives → negatives.
- Adjusted ORs: acceptance **1.68 [0.94–2.98]**; edge cases **1.29 [0.82–2.04]**.
- **Both primary intervals include 1.** Results are preliminary associations among resolved PRs.
- **Next:** expand balanced verification, validate detector accuracy, check historical specification versions.

*Secondary analysis. 1,322 unknowns; snapshot timing and tool/template differences limit interpretation.*
