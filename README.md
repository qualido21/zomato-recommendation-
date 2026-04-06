# 🍽️ Zomato AI Restaurant Recommender

An AI-powered restaurant recommendation system that combines structured Zomato data with an LLM to generate personalized, human-like recommendations.

## Project Structure

```
zomato-ai-recommender/
├── src/
│   ├── data/       ← Phase 1: Data Foundation
│   ├── filter/     ← Phase 2: Filtering Engine
│   ├── llm/        ← Phase 3: LLM Integration
│   └── api/        ← Phase 4: FastAPI Backend
├── frontend/       ← Phase 5: UI (Streamlit + Next.js)
├── tests/          ← Phase 6: Tests
├── data/           ← Generated cleaned dataset (Parquet)
└── docs/           ← Architecture & design docs
```

## Quickstart

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Run Phase 1 — Download & clean dataset
```bash
python -m src.data.loader
```

### 4. Run tests
```bash
pytest -v --cov=src
```

## Phases

| Phase | Status | Description |
|---|---|---|
| 1 — Data Foundation | ✅ | HuggingFace ingest, clean, Parquet |
| 2 — Filter Engine | 🔜 | Multi-criteria filtering |
| 3 — LLM Integration | 🔜 | Prompt engineering + LLM adapter |
| 4 — Backend API | 🔜 | FastAPI REST endpoints |
| 5 — Frontend | 🔜 | Streamlit MVP + Next.js |
| 6 — Testing & Eval | 🔜 | Full test suite |
| 7 — Deployment | 🔜 | Docker + CI/CD |

## Dataset

- **Source:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- **Library:** HuggingFace `datasets`

## Tech Stack

- **Backend:** FastAPI + Python 3.11
- **LLM:** OpenAI GPT-4o-mini / Google Gemini / Ollama
- **Data:** Pandas + Parquet
- **Frontend:** Streamlit (MVP) / Next.js (Production)
