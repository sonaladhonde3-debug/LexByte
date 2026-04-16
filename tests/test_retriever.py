from app.retriever import get_relevant_context, tokenize


def test_tokenize_removes_stop_words() -> None:
    tokens = tokenize("What is the deduction under section 80C for investment?")
    assert "what" not in tokens
    assert "80c" in tokens
    assert "investment" in tokens


def test_retriever_returns_80c_for_deduction_query() -> None:
    context = get_relevant_context("What is the maximum deduction under Section 80C?")
    assert context
    assert "80C" in context[0].section


def test_retriever_returns_empty_for_irrelevant_query() -> None:
    context = get_relevant_context("How to bake a chocolate cake without sugar?")
    assert context == []
