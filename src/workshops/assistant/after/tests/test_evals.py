"""The eval layer, proving the RAG layer. Offline, deterministic, no model."""

from assistant.evals import (
    BARS,
    GoldenRow,
    KeywordJudge,
    agreement,
    cohen_kappa,
    format_table,
    gate,
    is_abstention,
    run_suite,
    score_row,
)
from assistant.rag import RagStore

DOCS = [
    "approved refunds are processed within five business days",
    "credit note INV-88231 offsets invoice INV-88102 dated February nineteenth",
    "payments above ten thousand euro need two approvers recorded in the audit log",
    "ERR-4021 means the payment gateway timed out after thirty seconds",
]

GOLDEN = [
    GoldenRow("g-1", "semantic", "how long do refunds take",
              "approved refunds are processed within five business days",
              supporting_doc_ids=["0"]),
    GoldenRow("g-2", "exact", "INV-88231",
              "credit note INV-88231 offsets invoice INV-88102",
              supporting_doc_ids=["1"]),
    GoldenRow("g-3", "semantic", "who approves large payments",
              "payments above ten thousand euro need two approvers",
              supporting_doc_ids=["2"]),
    GoldenRow("g-4", "unanswerable", "what is next year's supplier budget cap",
              "not in the documents", expects_abstention=True),
    GoldenRow("g-5", "unanswerable", "how many people work in accounts payable",
              "not in the documents", expects_abstention=True),
]


def answer_with(store: RagStore, abstain_when_empty: bool = True):
    """The assistant's answer path: retrieve, then answer only from what came back."""

    def answer(question: str) -> tuple[str, list[str]]:
        contexts = store.search(question, k=2)
        if not contexts and abstain_when_empty:
            return "Not in the documents.", []
        return " ".join(contexts[:1]), contexts

    return answer


def honest_answer(question: str) -> tuple[str, list[str]]:
    """Retrieves, and abstains on the questions the corpus cannot support."""
    store = RagStore(DOCS)
    row = {r.question: r for r in GOLDEN}[question]
    if row.expects_abstention:
        return "Not in the documents.", []
    contexts = store.search(question, k=2)
    return contexts[0] if contexts else "Not in the documents.", contexts


def test_the_suite_scores_every_slice():
    result = run_suite(GOLDEN, honest_answer, KeywordJudge())
    assert set(result.by_slice) == {"semantic", "exact", "unanswerable"}
    assert len(result.rows) == len(GOLDEN)


def test_abstention_rows_are_scored_without_the_judge():
    row = GOLDEN[3]
    scored = score_row(row, "Not in the documents.", [], KeywordJudge())
    assert scored.judged is False
    assert scored.scores["faithfulness"] == 1.0


def test_an_invented_answer_fails_the_abstain_slice():
    result = run_suite(
        GOLDEN,
        lambda q: ("The cap is 40,000 EUR.", ["unrelated chunk"]),
        KeywordJudge(),
    )
    assert result.by_slice["unanswerable"]["faithfulness"] == 0.0


def test_the_gate_blocks_a_collapsed_slice_that_the_average_hides():
    baseline = {
        "semantic": {"faithfulness": 0.9, "context_recall": 0.9},
        "exact": {"faithfulness": 0.9, "context_recall": 0.9},
        "unanswerable": {"faithfulness": 1.0, "context_recall": 1.0},
    }
    abstain_questions = {r.question for r in GOLDEN if r.expects_abstention}

    def never_abstains(question: str) -> tuple[str, list[str]]:
        if question in abstain_questions:
            return "The cap is 40,000 EUR.", DOCS[:1]  # invents an answer instead
        return honest_answer(question)

    broken = run_suite(GOLDEN, never_abstains, KeywordJudge())
    problems = gate(broken, baseline)
    assert any("unanswerable" in p and "COLLAPSED" in p for p in problems)


def test_the_gate_passes_a_healthy_run():
    result = run_suite(GOLDEN, honest_answer, KeywordJudge())
    baseline = {name: dict(scores) for name, scores in result.by_slice.items()}
    assert gate(result, baseline) == []


def test_an_absolute_bar_breach_is_caught_without_any_baseline_movement():
    empty_store = RagStore([])
    result = run_suite(GOLDEN[:3], answer_with(empty_store), KeywordJudge())
    assert result.overall["context_recall"] < BARS["context_recall"]
    assert gate(result, {}) != []


def test_retrieval_actually_answers_the_exact_id_question():
    """The RAG layer's own promise, now measured instead of asserted."""
    result = run_suite([GOLDEN[1]], honest_answer, KeywordJudge())
    assert result.by_slice["exact"]["context_recall"] > 0.5


def test_kappa_exposes_a_rubber_stamp_judge_that_agreement_flatters():
    human = ["pass"] * 18 + ["fail"] * 2
    rubber_stamp = ["pass"] * 20
    assert agreement(human, rubber_stamp) == 0.9
    assert cohen_kappa(human, rubber_stamp, ("pass", "fail")) == 0.0


def test_kappa_is_one_when_you_and_the_judge_never_disagree():
    human = ["pass", "fail", "pass", "fail"]
    assert cohen_kappa(human, list(human), ("pass", "fail")) == 1.0


def test_abstention_phrasings_are_recognised():
    assert is_abstention("Not in the documents.")
    assert not is_abstention("Refunds take five business days.")


def test_the_table_reports_slices_and_an_overall_line():
    table = format_table(run_suite(GOLDEN, honest_answer, KeywordJudge()))
    assert "OVERALL" in table
    assert "unanswerable" in table
