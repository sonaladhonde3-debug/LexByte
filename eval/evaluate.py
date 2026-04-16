from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from app.llm import build_fallback_response, generate_tax_answer
from app.retriever import get_relevant_context
from app.schemas import TaxResponse

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_QUERY_PATH = PROJECT_ROOT / "eval" / "test_queries.json"

load_dotenv(PROJECT_ROOT / ".env")


async def evaluate_case(case: dict) -> dict:
    started_at = time.perf_counter()
    context = get_relevant_context(case["question"])
    if context:
        response = await generate_tax_answer(case["question"], context)
    else:
        response = build_fallback_response()
    latency = time.perf_counter() - started_at

    expected = set(case["expected_sections"])
    actual = set(response.applicable_sections)
    hit = expected.issubset(actual) if expected else response.confidence == 0.0

    return {
        "question": case["question"],
        "response": response.model_dump(),
        "latency_seconds": round(latency, 3),
        "section_match": hit,
        "json_valid": isinstance(response, TaxResponse),
        "fallback_ok": (response.confidence == 0.0) if case["should_fallback"] else True,
    }


async def main(limit: int | None = None) -> None:
    with TEST_QUERY_PATH.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if limit:
        cases = cases[:limit]

    results = await asyncio.gather(*(evaluate_case(case) for case in cases))

    total = len(results)
    section_hits = sum(result["section_match"] for result in results)
    valid_json = sum(result["json_valid"] for result in results)
    fallback_hits = sum(result["fallback_ok"] for result in results)
    latencies = sorted(result["latency_seconds"] for result in results)
    p95_index = min(total - 1, max(0, int(total * 0.95) - 1))

    summary = {
        "total_cases": total,
        "section_hit_rate": round(section_hits / total, 3),
        "json_validity_rate": round(valid_json / total, 3),
        "fallback_compliance_rate": round(fallback_hits / total, 3),
        "p95_latency_seconds": latencies[p95_index],
        "results": results,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the AI Tax Assistant on sample questions.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N test cases.")
    args = parser.parse_args()
    asyncio.run(main(limit=args.limit))
