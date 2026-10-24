# HealthDoc AI 🏥

**An AI-powered healthcare document intelligence platform for extracting, searching, and understanding information from uploaded documents.**

HealthDoc AI helps users explore healthcare and insurance documents through document processing, OCR, evidence-based retrieval, source citations, and question answering. It is designed to make lengthy documents easier to navigate while keeping answers grounded in the original source material.

## ✨ Features

- **Document Upload & Processing** — Upload supported documents for extraction and indexing.
- **OCR Support** — Extract text from scanned documents and image-based PDFs using Tesseract OCR and OpenCV preprocessing.
- **Document Search** — Retrieve relevant passages from processed documents using a hybrid retrieval pipeline.
- **Evidence-Based Question Answering** — Answer questions using relevant passages from uploaded documents.
- **Source Citations** — Link answer excerpts to document pages and validate citations against stored source text.
- **Extractive Fallback** — Return relevant source sentences when an external language model is unavailable.
- **Conversation Context** — Support follow-up questions in chat.
- **Document Insights** — Extract entities, definitions, and structured fields from document text.
- **Evaluation & Analytics** — Measure retrieval and answer-quality metrics to help assess system performance.
- **Privacy-Aware Design** — Process documents locally by default; when an external LLM provider is configured, retrieved passages may be sent to that provider for answer generation.

## 🛠️ Tech Stack

| Component            | Technology                                      |
| -------------------- | ----------------------------------------------- |
| Backend              | Python, FastAPI                                 |
| Frontend             | React, Vite                                     |
| Database             | SQLite                                          |
| Document Processing  | PyMuPDF / PDF parsing                           |
| OCR                  | Tesseract OCR, pytesseract, OpenCV              |
| NLP                  | spaCy, custom text-processing utilities         |
| Retrieval            | Hybrid retrieval, TF-IDF-based lexical fallback |
| LLM Integration      | OpenAI-compatible API adapter                   |
| Testing & Evaluation | Custom evaluation pipeline                      |

## 🏗️ How It Works

1. **Upload:** A user uploads a supported healthcare or insurance document.
2. **Extract:** The system extracts document text and uses OCR when required.
3. **Process:** The extracted text is divided into chunks and stored for retrieval.
4. **Retrieve:** A question is used to find relevant passages from the selected documents.
5. **Validate:** Candidate evidence and citations are checked against the stored source text.
6. **Answer:** The system generates a response using an optional configured LLM. If generation fails, it can fall back to relevant source sentences.
7. **Review:** The user can inspect the answer and its supporting document citations.

## 📂 Project Structure

```text
healthdoc-ai/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── db/
│   │   └── services/
│   │       ├── analytics/
│   │       ├── embeddings/
│   │       ├── evaluation/
│   │       ├── ingestion/
│   │       ├── nlp/
│   │       ├── ocr/
│   │       ├── rag/
│   │       └── retrieval/
│   ├── tests/
│   └── requirements.txt
├── frontend/
├── .env.example
├── .gitignore
└── README.md
```

*The structure above is representative; adjust it if your actual repository differs.*

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or a compatible project-supported version
- Node.js and npm
- Tesseract OCR for scanned-document processing
- Git (optional, if cloning the repository)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd healthdoc-ai
```

Replace the repository URL with your actual GitHub repository URL.

### 2. Configure the Backend

Open a terminal in the `backend` directory.

Create and activate a virtual environment:

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install -r requirements.txt
```

If the project uses additional optional dependency files, install those only when needed.

### 3. Configure Environment Variables

Create a `.env` file in the repository root by copying `.env.example`.

```powershell
Copy-Item .env.example .env
```

Review the settings and adjust them for your environment. For optional LLM generation, configure the provider, base URL, model, and API key according to the provider's documentation.

**Never commit your real `.env` file or API keys.** Keep `.env.example` limited to safe defaults and placeholders.

### 4. Start the Backend

From the `backend` directory:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 5. Start the Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, typically:

```text
http://localhost:5173
```

> These commands reflect the current development setup; check the repository's dependency files and application configuration if your environment differs.

## 🤖 Language Model Configuration

HealthDoc AI supports an optional language-model adapter compatible with the OpenAI chat-completions API format.

When configured, retrieved document passages are sent to the selected provider for generation. When no LLM is configured, the application can provide extractive answers from retrieved source text.

External model availability, quotas, and response times depend on the configured provider. LLM-generated answers should be tested separately from the offline retrieval and extractive fallback.

## 🔐 Privacy & Responsible Use

- Uploaded documents may contain sensitive healthcare or insurance information. Use synthetic or non-sensitive documents for development and testing.
- Documents are processed locally by default.
- Configuring an external LLM changes the data flow: retrieved passages may be sent to the provider.
- Citation validation helps verify source grounding but does not guarantee that every generated statement is correct.
- This project is intended for document understanding and educational use. It is not a substitute for professional medical, insurance, or legal advice.
- Do not use the application as a clinically validated decision-support system.

## 🧪 Testing & Evaluation

Run the project's available tests from the backend directory:

```powershell
python -m pytest
```

This command assumes pytest and the project tests are installed. Review the test configuration and requirements before running it.

The project also includes an evaluation pipeline for measuring aspects of retrieval and answer quality. Evaluation results depend on the dataset and test cases used; they do not establish clinical validity.

## 🗺️ Roadmap

- [ ] Improve LLM reliability, timeout handling, and retry behavior.
- [ ] Expand automated tests for retrieval, citations, and provider failures.
- [ ] Improve evaluation coverage for scanned and text-based documents.
- [ ] Refine document-processing and error-reporting workflows.
- [ ] Add deployment documentation and production-readiness checks.

## 👩‍💻 Author

**Himanshi**

GitHub: [@himanshi047272](https://github.com/himanshi047272)

---

*Built as an AI/ML project exploring document intelligence, OCR, NLP, information retrieval, and evidence-grounded question answering.*
