"""Executive Orchestrator, Etapa 2 -- Selection Rules determinísticas
(Founder Decision "Implementação do Executive Orchestrator", Garantia 1).
Ainda sem correlação, ainda sem execução de Advisors -- prova exclusivamente
o mecanismo de seleção em isolamento."""
import ast
import inspect

from src.services.executive_orchestrator import selection_rule as selection_rule_module
from src.services.executive_orchestrator.selection_rule import (
    OrchestrationScope,
    SelectionSignals,
    evaluate_selection_rule,
)


class TestNeverTheLlm:
    def test_module_never_imports_an_llm_provider(self):
        tree = ast.parse(inspect.getsource(selection_rule_module))
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert not any("llm" in name.lower() for name in imported_names)

    def test_evaluate_selection_rule_never_accepts_an_llm_related_parameter(self):
        parameters = inspect.signature(evaluate_selection_rule).parameters
        assert not any("llm" in name.lower() for name in parameters)


class TestDeterminismAndRepeatability:
    def test_same_signals_always_produce_the_same_selection(self):
        signals = SelectionSignals(explicit=frozenset({"risco"}))

        first = evaluate_selection_rule(signals)
        second = evaluate_selection_rule(signals)
        third = evaluate_selection_rule(signals)

        assert first.selected == second.selected == third.selected
        assert [identity.name for identity in first.selected] == ["risk_advisor"]

    def test_same_question_repeated_always_selects_the_same_advisors(self):
        signals = SelectionSignals(question="Qual o status de entrega e os riscos deste projeto?")

        outcomes = [evaluate_selection_rule(signals) for _ in range(5)]

        names = {tuple(identity.name for identity in outcome.selected) for outcome in outcomes}
        assert len(names) == 1


class TestExplicitSignals:
    def test_explicit_signal_selects_exactly_the_matching_advisor(self):
        outcome = evaluate_selection_rule(SelectionSignals(explicit=frozenset({"estratégia"})))

        assert [identity.name for identity in outcome.selected] == ["strategy_advisor"]

    def test_explicit_signal_by_advisor_name_also_matches(self):
        outcome = evaluate_selection_rule(SelectionSignals(explicit=frozenset({"risk_advisor"})))

        assert [identity.name for identity in outcome.selected] == ["risk_advisor"]

    def test_multiple_explicit_signals_select_multiple_advisors(self):
        outcome = evaluate_selection_rule(
            SelectionSignals(explicit=frozenset({"risco", "entrega"}))
        )

        assert {identity.name for identity in outcome.selected} == {"risk_advisor", "delivery_advisor"}

    def test_explicit_takes_precedence_over_question_text(self):
        # The question text is full of risk/delivery vocabulary, but an
        # explicit signal for strategy alone must select only Strategy.
        signals = SelectionSignals(
            explicit=frozenset({"estratégia"}),
            question="Quais os riscos e o status de entrega deste projeto?",
        )

        outcome = evaluate_selection_rule(signals)

        assert [identity.name for identity in outcome.selected] == ["strategy_advisor"]


class TestImplicitLexicalFallback:
    def test_question_text_alone_selects_the_matching_advisor(self):
        outcome = evaluate_selection_rule(
            SelectionSignals(question="Existe algum risco de escalação neste projeto?")
        )

        assert [identity.name for identity in outcome.selected] == ["risk_advisor"]

    def test_question_text_may_select_more_than_one_advisor(self):
        outcome = evaluate_selection_rule(
            SelectionSignals(question="Qual o status de entrega e os riscos deste projeto?")
        )

        assert {identity.name for identity in outcome.selected} == {"delivery_advisor", "risk_advisor"}


class TestSelectionEmpty:
    def test_no_explicit_signals_and_irrelevant_question_selects_nobody(self):
        outcome = evaluate_selection_rule(SelectionSignals(question="Qual a previsão do tempo hoje?"))

        assert outcome.selected == ()

    def test_empty_signals_altogether_select_nobody(self):
        outcome = evaluate_selection_rule(SelectionSignals())

        assert outcome.selected == ()


class TestPortfolioAdvisorStructuralPrecondition:
    def test_portfolio_advisor_never_selected_without_a_portfolio_id(self):
        outcome = evaluate_selection_rule(SelectionSignals(explicit=frozenset({"portfólio"})))

        assert outcome.selected == ()

    def test_portfolio_advisor_selected_once_a_portfolio_id_is_supplied(self):
        signals = SelectionSignals(
            explicit=frozenset({"portfólio"}),
            scope=OrchestrationScope(portfolio_id=42),
        )

        outcome = evaluate_selection_rule(signals)

        assert [identity.name for identity in outcome.selected] == ["portfolio_advisor"]

    def test_other_advisors_are_unaffected_by_the_precondition(self):
        signals = SelectionSignals(explicit=frozenset({"risco", "portfólio"}))

        outcome = evaluate_selection_rule(signals)

        assert {identity.name for identity in outcome.selected} == {"risk_advisor"}


class TestSelectionTraceEntry:
    def test_trace_entry_records_explicit_signals_and_selected_names(self):
        outcome = evaluate_selection_rule(SelectionSignals(explicit=frozenset({"risco"})))

        assert outcome.trace_entry.signals == ("risco",)
        assert outcome.trace_entry.selected_advisor_names == ("risk_advisor",)

    def test_trace_entry_records_the_question_when_no_explicit_signal_is_given(self):
        outcome = evaluate_selection_rule(SelectionSignals(question="Existe risco neste projeto?"))

        assert outcome.trace_entry.signals == ("Existe risco neste projeto?",)

    def test_trace_entry_is_produced_even_for_an_empty_selection(self):
        outcome = evaluate_selection_rule(SelectionSignals(question="irrelevante"))

        assert outcome.trace_entry.selected_advisor_names == ()
