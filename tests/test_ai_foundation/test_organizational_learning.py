"""Package M (V1 Product & Capability Completion): the pure recurrence
algorithm, no database needed -- same deterministic rule as
`web/lib/organizational-intelligence/organizational-learnings.ts`.
"""
from src.services.ai_foundation.organizational_learning import (
    OrganizationalLearning,
    build_recurring_actions,
    build_recurring_risks,
    select_top_learnings,
)


def _risk(project_name, description):
    return {"project_name": project_name, "description": description}


def test_a_description_repeated_in_3_distinct_projects_is_a_learning():
    risks = [_risk(p, "Atraso de fornecedor") for p in ["Aurora", "Boreal", "Cedro"]]

    learnings = build_recurring_risks(risks)

    assert len(learnings) == 1
    assert learnings[0] == OrganizationalLearning(
        category="risco",
        description="Atraso de fornecedor",
        occurrences=3,
        project_names=("Aurora", "Boreal", "Cedro"),
    )


def test_a_description_repeated_in_only_2_projects_is_not_a_learning():
    risks = [_risk(p, "Risco isolado") for p in ["Aurora", "Boreal"]]

    assert build_recurring_risks(risks) == []


def test_the_same_project_repeating_a_description_counts_once():
    risks = [_risk("Aurora", "Mesmo risco 3 vezes")] * 3

    assert build_recurring_risks(risks) == []


def test_an_entry_with_no_project_name_never_counts_toward_recurrence():
    risks = [_risk(None, "Sem projeto")] * 5

    assert build_recurring_risks(risks) == []


def test_sorted_by_occurrences_desc_then_description_asc():
    risks = (
        [_risk(p, "B baixa recorrencia") for p in ["Aurora", "Boreal", "Cedro"]]
        + [_risk(p, "A alta recorrencia") for p in ["Aurora", "Boreal", "Cedro", "Delta"]]
    )

    learnings = build_recurring_risks(risks)

    assert [item.description for item in learnings] == ["A alta recorrencia", "B baixa recorrencia"]


def test_build_recurring_actions_uses_the_acao_category():
    actions = [_risk(p, "Mesma acao pendente") for p in ["Aurora", "Boreal", "Cedro"]]

    learnings = build_recurring_actions(actions)

    assert learnings[0].category == "acao"


def test_select_top_learnings_caps_at_the_limit_in_fixed_category_order():
    risks = [
        OrganizationalLearning("risco", f"risco {i}", 3, ("Aurora", "Boreal", "Cedro"))
        for i in range(4)
    ]
    actions = [
        OrganizationalLearning("acao", f"acao {i}", 3, ("Aurora", "Boreal", "Cedro")) for i in range(4)
    ]

    top = select_top_learnings(risks, actions, limit=5)

    assert len(top) == 5
    assert [item.category for item in top] == ["risco", "risco", "risco", "risco", "acao"]


def test_select_top_learnings_never_fabricates_items_to_reach_the_limit():
    risks = [OrganizationalLearning("risco", "unico risco", 3, ("Aurora", "Boreal", "Cedro"))]

    assert select_top_learnings(risks, [], limit=5) == risks
