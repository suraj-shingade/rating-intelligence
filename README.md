# Rating Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C.svg?logo=langchain&logoColor=white)](https://www.langchain.com/)
[![Anthropic Claude](https://img.shields.io/badge/Anthropic-Claude-D97757.svg)](https://www.anthropic.com/)
[![Weaviate](https://img.shields.io/badge/Weaviate-1.28-00C7B7.svg)](https://weaviate.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

> RAG-powered credit research assistant for rating analysts — semantic methodology search, draft credit assessment generation, peer comparison, and surveillance alert drafting.

## Features

- **Semantic methodology search** over rating criteria documents via Weaviate vector store
- **Draft credit assessments** grounded in retrieved methodology chunks and issuer financials
- **Peer comparison analysis** across sectors
- **Surveillance alert drafting** for rating changes
- **Structured logging** with correlation IDs and token-usage tracking
- **Typed React frontend** with Vite

## Architecture

```
┌──────────────┐      ┌──────────────────┐      ┌───────────────┐
│  React (Vite)│ ───▶ │  FastAPI backend │ ───▶ │  Claude (LLM) │
└──────────────┘      │   (LangChain)    │      └───────────────┘
                     │                  │
                     │                  │ ───▶ ┌───────────────┐
                     └──────────────────┘      │   Weaviate    │
                                               └───────────────┘
```

## Tech Stack

| Layer     | Tools                                                       |
| --------- | ----------------------------------------------------------- |
| Backend   | Python 3.12, FastAPI, LangChain, Pydantic, structlog        |
| LLM       | Anthropic Claude (via `langchain-anthropic`)                |
| Vector DB | Weaviate + `text2vec-transformers` (all-MiniLM-L6-v2)       |
| Frontend  | React 18, TypeScript 5, Vite 5, React Router                |
| Infra     | Docker, docker-compose                                      |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & docker-compose
- Anthropic API key

### 1. Configure environment

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY
```

### 2. Run with Docker (recommended)

```bash
docker-compose up --build
```

This starts Weaviate, the transformers inference container, and the FastAPI backend on `http://localhost:8000`.

### 3. Ingest the sample knowledge base

```bash
python scripts/ingest_knowledge_base.py
```

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The app is served at `http://localhost:5173`.

## Local Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Project Structure

```
.
├── main.py                 # FastAPI entry point
├── src/
│   ├── api/                # Route handlers
│   ├── services/           # LLM, Weaviate, document processing, pipeline
│   ├── models/             # Domain models
│   ├── config.py           # Settings loader
│   ├── exceptions.py
│   └── logging_config.py
├── scripts/
│   └── ingest_knowledge_base.py
├── config/settings.yaml    # Application configuration
├── data/knowledge_base/    # Sample methodology docs & financials
├── frontend/               # React + Vite client
├── Dockerfile
└── docker-compose.yml
```

## API

Once running, interactive docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

```bash
pytest
```

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss substantial changes.

## License

Released under the [MIT License](LICENSE).
