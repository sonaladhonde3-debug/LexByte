from fastapi.testclient import TestClient

from app.main import create_app
from app.routes import get_llm_service, get_retriever
from app.schemas import ContextChunk, TaxResponse


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_endpoint() -> None:
    app = create_app()

    def fake_retriever(_: str):
        return [
            ContextChunk(
                section="80C",
                title="Fake",
                description="Fake context",
                details=["Cap is Rs 1,50,000."],
                keywords=["80c"],
                tax_year="FY 2025-26",
                score=5.0,
            )
        ]

    async def fake_llm(question: str, context: list) -> TaxResponse:
        assert question
        assert context[0].section == "80C"
        return TaxResponse(
            answer="Section 80C permits an aggregate deduction up to Rs 1,50,000.",
            applicable_sections=["80C"],
            confidence=0.92,
            note="This is not legal or financial advice. Consult a professional.",
        )

    app.dependency_overrides[get_retriever] = lambda: fake_retriever
    app.dependency_overrides[get_llm_service] = lambda: fake_llm

    client = TestClient(app)
    response = client.post("/ask", json={"question": "What is the deduction under 80C?"})
    assert response.status_code == 200
    assert response.json()["applicable_sections"] == ["80C"]


def test_ask_endpoint_returns_404_when_no_context() -> None:
    app = create_app()
    app.dependency_overrides[get_retriever] = lambda: lambda _: []
    client = TestClient(app)

    response = client.post("/ask", json={"question": "What is GST on gold?"})
    assert response.status_code == 404
