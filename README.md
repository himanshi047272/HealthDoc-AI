# HealthDoc AI

Upload healthcare-related PDFs or scans, ask questions, and get answers that point to the exact document and page they came from. If the documents don't say, the app says so instead of guessing.

This is an educational document-search tool. It is not a diagnostic system, an insurance decision engine, or a replacement for professional advice. All bundled documents are **synthetic**.

Screenshots: _pending (the frontend has not been built or run in the environment this was written in)._

## What works without any API key
Upload and validation, PDF text extraction, OCR for scans and images, chunking, keyword + vector search, cited extractive answers, abstention, conflict reporting, insights, analytics, evaluation. Nothing leaves your machine unless you set `HEALTHDOC_LLM_PROVIDER`.

## Run it
```bash
cp .env.example .env
# backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
sudo apt install tesseract-ocr poppler-utils      # macOS: brew install tesseract poppler
uvicorn app.main:app --reload --port 8000          # docs: http://localhost:8000/docs
# frontend (second terminal)
cd frontend && npm install && npm run dev          # http://localhost:5173
```
Docker: `docker compose up --build` → UI on :8080, API on :8000. Add `--build-arg ML=1` to the backend build for sentence-transformers.
Reset data: stop the server and delete `backend/data/` (or `docker volume rm <project>_healthdoc-data`).

## Tests
```bash
cd backend && python -m unittest discover -s app/tests -t . -v     # or: pytest
cd frontend && npm test            # Vitest
cd frontend && npx playwright install chromium && npm run e2e
./scripts/run_tests.sh             # backend + frontend
cd frontend && npm run build       # type-check + production build
```

## How it works
```
upload → validate (extension, signature, MIME, size) → store under a generated name
  → PyMuPDF/pypdf text per page → pages with little text → rasterise → OpenCV → Tesseract
  → strip repeated headers/footers → normalise → sentence-aligned chunks (page kept)
  → verify embeddings build → status "ready"
question → BM25 + vector scores (max-normalised, averaged) → de-duplicate → drop sentences that look like
  instructions → abstain if a question term appears nowhere in scope → pick evidence sentences
  → (optional LLM, output checked: citations must exist, quotes must be verbatim) → validate every citation
```
- **Retrieval:** default vectors are character n-gram TF-IDF. They handle word forms ("excluded"/"exclusions") but are *not* semantic. For real semantic matching set `HEALTHDOC_EMBEDDER=sbert`. That path is written but was **not run** here (no network to download a model).
- **Storage:** stdlib `sqlite3` repository (not SQLAlchemy) so it runs with no extra install. A numpy/scipy matrix is used as the vector index (FAISS is not used).
- **Abstention rule:** answer only if every content term of the question occurs somewhere in the selected documents, and IDF-weighted term coverage ≥ `fixtures/calibration.json`. The first rule does almost all the work on the test set; the threshold is close to inert there.
- **Conflicts:** when documents in scope give different numbers for the same question, both are shown with their sources.
- **Injection:** sentences matching instruction-like patterns are removed from evidence; the LLM prompt marks evidence as untrusted data.

## Evaluation (measured, synthetic, 35 questions over 3 fixture PDFs)
Reproduce: `python scripts/calibrate.py` then see `docs/eval_results.json` (or press *Run evaluation* in the UI). Full output is committed in `docs/eval_results.json`.

| Metric | Result |
|---|---|
| Recall@5 (expected doc+page found) | 1.00 |
| MRR | 0.94 |
| Answer/abstain precision · recall | 1.00 · 0.93 |
| Correct abstention (7 unanswerable) | 7/7 |
| Answer support (expected facts in cited text) | 0.86 (0.92 excluding the 2 paraphrase cases) |
| Citation validity | 1.00 |
| Citation precision | **0.74** (below 0.85) |
| Conflict cases detected · false conflicts | 2/2 · 0 |
| Processing success | 3/3 |

Misses: q12 and q22 (the question says "documents", the text says "itemized bill"), q27 and q28 (deliberate paraphrases the lexical fallback can't match).
Limits: tiny, hand-written corpus; the threshold was fit on the same questions (leave-one-out gives the same decision numbers); the unseen-term rule was added after looking at failures; none of this measures clinical accuracy or behaviour on your own files. Citation precision is low because tied sentences are all shown instead of guessing.

## Known limitations
- Frontend, FastAPI routes, Docker images and Playwright flow were **written but never executed** (no network to install packages). Backend API tests are skipped for the same reason.
- Pinned versions in `requirements*.txt` and `package.json` are unverified. Run `pip freeze > requirements.lock` / commit `package-lock.json` after first install.
- No spaCy model, PyMuPDF, sentence-transformers or FAISS was available; fallbacks (regex entities, pypdf, TF-IDF, numpy) were what ran.
- Classification is a keyword baseline, not a trained model. No model is fine-tuned.
- OCR output can be wrong; pages show OCR confidence and are labelled.
- No authentication: don't expose it to the internet as is.

## Privacy
Files and extracted text stay in `HEALTHDOC_DATA_DIR`. Deleting a document removes its file, pages, chunks and citations. Logs record error types, not document text. If an LLM provider is configured, retrieved passages and the question are sent to it. Settings shows this. Keys live only in server environment variables.

## Deploy
Backend: any container host with a persistent volume at `/data` (`backend/Dockerfile`). Frontend: static build served by nginx (`frontend/Dockerfile`) or any static host; set `VITE_API_URL` at build time if the API is on another origin and add that origin to `HEALTHDOC_CORS_ORIGINS`. Not deployed or verified.
