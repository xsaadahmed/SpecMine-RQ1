import pytest
from features import structural_features


@pytest.mark.parametrize("text,ac,edge",[
    ("## Acceptance Criteria\n- must work\n## Edge Cases\n- empty input",1,1),
    ("Acceptance Criteria\n===================\nSomething",1,0),
    ("**Edge Cases**:\n- none",0,1),
    ("## 3. Acceptance criteria\n",1,0),
    ("```markdown\n## Acceptance Criteria\n```\ntext",0,0),
    ("<!--\n## Edge Cases\n-->\ntext",0,0),
    ("This paragraph mentions acceptance criteria and edge cases.",0,0),
    ("## Unrelated\n### Edge-case handling\n",0,1),
    ("## 验收标准\n",0,0),
])
def test_structural_rules_and_limits(text,ac,edge):
    f=structural_features(text)
    assert f['has_acceptance_criteria']==ac
    assert f['has_edge_cases']==edge


def test_directive_rule_is_reused_without_heading_invention():
    assert structural_features("Must add unit tests for empty input.")['has_testing_requirement']==1
    assert structural_features("## Testing\nNo unit tests required.")['has_testing_requirement']==0
