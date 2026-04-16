# AI Tax Assistant

A production-oriented Indian Income Tax assistant built with FastAPI, Retrieval-Augmented Generation (RAG), and the OpenAI API.

## What this project does

- Exposes a `POST /ask` endpoint that accepts a tax-related question.
- Retrieves relevant context from extracted PDF, DOCX, or TXT tax documents placed in `documents/`.
- Sends only that retrieved context to the language model.
- Returns a structured JSON response with `answer`, `applicable_sections`, `confidence`, and `note`.
- Includes sample evaluation logic, sample queries, and unit tests.

## Project structure

```text
app/
  main.py
  routes.py
  retriever.py
  llm.py
  prompts.py
  schemas.py
  ingest.py
documents/
  your_tax_pdfs_here.pdf
data/
  document_chunks.json
  tax_data.json
eval/
  evaluate.py
  test_queries.json
tests/
  test_routes.py
  test_retriever.py
  test_llm.py
```

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.

## Add your tax documents

Place your source files in:

```text
documents/
```

Supported file types:

- PDF
- DOCX
- TXT

Examples:

- `income_tax_act_1961.pdf`
- `income_tax_rules_1962.pdf`
- `cbdt_circular_2025_01.pdf`
- `cbdt_notification_2025_03.pdf`

## Build the searchable chunk index

Run this once after adding or updating documents:

```bash
python -m app.ingest
```

This creates:

```text
data/document_chunks.json
```

The API will search this chunk file first. If it is missing or empty, it falls back to the sample `tax_data.json`.

## Run the API

```bash
uvicorn app.main:app --reload
```

## API examples

### Health check

```bash
curl http://127.0.0.1:8000/health
```

### Ask a tax question

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What is the maximum deduction under Section 80C?\"}"
```

Example response:

```json
{
  "answer": "Section 80C provides an aggregate deduction up to Rs 1,50,000 for eligible investments and payments covered by the retrieved context.",
  "applicable_sections": ["80C"],
  "confidence": 0.93,
  "note": "This response is based only on the retrieved statutory context and is not legal or financial advice. Please consult a chartered accountant or tax professional."
}
```

## Evaluation

Run the evaluator against the sample query set:

```bash
python -m eval.evaluate
```

The evaluator reports section hit rate, JSON validity rate, fallback compliance rate, and p95 latency.

## Testing

```bash
pytest
```

## Design notes

- Retrieval is keyword-based today for clarity and traceability.
- Document ingestion is local and chunk-based for clarity and traceability.
- The retriever interface is intentionally simple so it can be upgraded to vector search later.
- The LLM is instructed to answer only from supplied context and to return `insufficient context` when the dataset does not support an answer.
- The OpenAI integration uses structured outputs so schema validation is enforced twice: once by the model response format and again by Pydantic validation in the app.

## Sample questions

- What is the maximum deduction under Section 80C?
- Can I claim both 80C and 80D in the same year?
- What deductions are available on a home loan?
- What is the GST rate on gold jewellery?

## Next production upgrades

- Replace keyword retrieval with embeddings plus vector search.
- Add request authentication and rate limiting.
- Add audit logging and observability.
- Expand the dataset with versioned tax-year coverage.
- Add a secondary answer validator for low-confidence outputs.
