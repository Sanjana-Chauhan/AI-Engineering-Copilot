# Engineering Copilot

An AI-powered developer assistant designed for repository-level code understanding, semantic code search, and context-aware question answering.

The project combines **Next.js, TypeScript, Python, FastAPI, embeddings, ChromaDB, RAG, and Gemini** to create an AI assistant capable of understanding and answering questions about a software repository.

---

## Current Status

**Version:** V1 - Repository RAG Foundation

The current version supports:

* AI-powered chat using Gemini
* Repository scanning
* Source-code ingestion
* Code chunking
* Code embeddings
* Persistent vector storage using ChromaDB
* Semantic code search
* Repository-aware RAG responses
* Source metadata including file path, language, and line ranges

---

## Architecture

```text
                         Engineering Copilot
                                |
                                v
                         Next.js Frontend
                                |
                                v
                          FastAPI Backend
                                |
              +-----------------+-----------------+
              |                 |                 |
              v                 v                 v
         Chat Service    Repository Service   RAG Service
                                |                 |
                                v                 v
                         Source Code        Semantic Search
                                |                 |
                                v                 v
                           Chunking          ChromaDB
                                |                 |
                                +--------+--------+
                                         |
                                         v
                                  Retrieved Context
                                         |
                                         v
                                      Gemini
                                         |
                                         v
                                AI Generated Answer
```

---

## Technology Stack

### Frontend

* Next.js
* TypeScript
* React

### Backend

* Python
* FastAPI
* Pydantic

### AI

* Google Gemini API
* Sentence Transformers
* Embeddings
* Retrieval-Augmented Generation (RAG)

### Vector Storage

* ChromaDB

### Development

* Python virtual environment
* REST APIs
* Swagger / OpenAPI

---

# Features

## 1. AI Chat

The application can communicate with Gemini through a FastAPI backend.

Current flow:

```text
User
  |
  v
Next.js
  |
  v
POST /api/chat
  |
  v
FastAPI
  |
  v
LLM Service
  |
  v
Gemini
  |
  v
AI Response
```

Example request:

```json
{
  "message": "Explain Python decorators"
}
```

---

## 2. Repository Scanning

The backend can recursively scan a local repository and identify relevant source files.

The scanner:

* Recursively searches directories
* Detects supported source files
* Ignores unnecessary directories
* Returns relative file paths

Ignored directories include:

```text
.git
node_modules
venv
__pycache__
.next
dist
build
```

Supported file types currently include:

```text
.py
.js
.jsx
.ts
.tsx
.java
.cpp
.c
.cs
.go
.rs
.html
.css
.json
.md
```

---

## 3. Source-Code Ingestion

Repositories can be ingested through:

```text
POST /api/repository/ingest
```

The ingestion pipeline is:

```text
Repository
    |
    v
File Discovery
    |
    v
Read Source Files
    |
    v
Code Chunking
    |
    v
Embeddings
    |
    v
ChromaDB
```

---

## 4. Code Chunking

Source files are divided into smaller chunks before being embedded.

Each chunk contains metadata:

```json
{
  "content": "source code...",
  "file_path": "app/services/llm_service.py",
  "language": "python",
  "start_line": 1,
  "end_line": 20
}
```

This metadata allows the retrieval system to identify where a piece of code came from.

---

## 5. Embeddings

The project uses a Sentence Transformer model to convert source-code chunks into vector representations.

Current embedding model:

```text
all-MiniLM-L6-v2
```

Conceptually:

```text
Source Code
    |
    v
Embedding Model
    |
    v
Vector Representation
    |
    v
Vector Database
```

Embeddings allow the system to search based on semantic meaning rather than simple keyword matching.

---

## 6. Vector Storage

The project uses **ChromaDB** as the local vector database.

ChromaDB stores:

* Code chunks
* Embeddings
* File metadata
* Line information

The vector database is persisted locally under:

```text
data/chroma/
```

The generated database files should not be committed to Git.

---

## 7. Semantic Code Search

The project provides:

```text
GET /api/search/code
```

A user can ask questions such as:

```text
Where is authentication handled?
```

or:

```text
How does repository ingestion work?
```

The system performs semantic retrieval and returns relevant source-code chunks.

The flow is:

```text
User Query
    |
    v
Query Embedding
    |
    v
Vector Similarity Search
    |
    v
Relevant Code Chunks
```

---

# 8. Repository RAG

The current system combines semantic retrieval with Gemini to create repository-aware answers.

Endpoint:

```text
GET /api/rag/ask
```

The pipeline is:

```text
User Question
      |
      v
Semantic Search
      |
      v
Relevant Code Chunks
      |
      v
Context Builder
      |
      v
Prompt Construction
      |
      v
Gemini
      |
      v
Repository-Aware Answer
```

The RAG prompt instructs the model to:

* Use repository context as the primary source
* Avoid inventing files or code
* Mention relevant file paths
* Mention line numbers when available
* Indicate when the available context is insufficient

---

# Project Structure

```text
AI-Engineering-Copilot/
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── models/
│   │   │   ├── chat.py
│   │   │   └── code.py
│   │   │
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   ├── repository.py
│   │   │   ├── ingestion.py
│   │   │   ├── search.py
│   │   │   └── rag.py
│   │   │
│   │   ├── services/
│   │   │   ├── llm_service.py
│   │   │   ├── repository_service.py
│   │   │   ├── code_service.py
│   │   │   ├── vector_store.py
│   │   │   ├── search_service.py
│   │   │   └── rag_service.py
│   │   │
│   │   └── main.py
│   │
│   ├── data/
│   │   └── chroma/
│   │
│   ├── .env
│   ├── requirements.txt
│   └── venv/
│
├── frontend/
│   └── Next.js application
│
└── README.md
```

---

# API Endpoints

## Chat

```text
POST /api/chat
```

Example:

```json
{
  "message": "Explain dependency injection"
}
```

---

## Repository Scan

```text
GET /api/repository/scan
```

Example:

```text
/api/repository/scan?repository_path=C:\path\to\repository
```

---

## Repository Ingestion

```text
POST /api/repository/ingest
```

Example:

```text
/api/repository/ingest?repository_path=C:\path\to\repository
```

---

## Semantic Code Search

```text
GET /api/search/code
```

Example:

```text
/api/search/code?query=Where%20is%20authentication%20handled
```

Optional:

```text
limit=5
```

---

## Repository RAG

```text
GET /api/rag/ask
```

Example:

```text
/api/rag/ask?question=How%20does%20repository%20ingestion%20work
```

---

# Environment Setup

Create a `.env` file inside the backend:

```env
GEMINI_API_KEY=your_api_key
```

Do not commit the `.env` file.

Add it to `.gitignore`:

```text
.env
venv/
data/
__pycache__/
```

---

# Running the Backend

Navigate to the backend:

```powershell
cd backend
```

Activate the virtual environment:

```powershell
venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start FastAPI:

```powershell
uvicorn app.main:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Running the Frontend

Navigate to the frontend:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

The application will normally be available at:

```text
http://localhost:3000
```

---

# RAG Pipeline

The current implementation follows this architecture:

```text
             Repository
                  |
                  v
          File Discovery
                  |
                  v
           Source Reading
                  |
                  v
            Code Chunking
                  |
                  v
          Embedding Model
                  |
                  v
             ChromaDB
                  |
                  v
          Semantic Retrieval
                  |
                  v
           Context Builder
                  |
                  v
          Prompt Orchestration
                  |
                  v
              Gemini
                  |
                  v
        Repository-Aware Answer
```

---

# Current Limitations

This is currently an MVP implementation.

The following areas are planned but not yet implemented:

* Conversation memory
* Repository isolation
* Incremental repository ingestion
* Duplicate ingestion handling
* Improved code-aware chunking
* Advanced metadata filtering
* Retrieval reranking
* Source citation objects in API responses
* Streaming LLM responses
* AI tool calling
* Repository file exploration tools
* Code debugging workflow
* Code explanation workflow
* GitHub repository integration
* Authentication
* Production deployment
* RAG evaluation and quality metrics

---

# Roadmap

## Phase 1 — Foundation

* [x] Next.js frontend
* [x] FastAPI backend
* [x] Gemini integration
* [x] Chat API
* [x] Repository scanner
* [x] Source-code ingestion
* [x] Code chunking

## Phase 2 — RAG

* [x] Embeddings
* [x] ChromaDB
* [x] Semantic search
* [x] Context construction
* [x] Gemini + retrieved context
* [x] Repository-aware responses

## Phase 3 — Advanced RAG

* [ ] Repository isolation
* [ ] Incremental ingestion
* [ ] Duplicate detection
* [ ] Better chunking
* [ ] Metadata filtering
* [ ] Retrieval reranking
* [ ] Source attribution

## Phase 4 — AI Agent

* [ ] Tool calling
* [ ] `search_code`
* [ ] `read_file`
* [ ] `list_files`
* [ ] `find_references`
* [ ] Agentic workflows

## Phase 5 — Developer Workflows

* [ ] Code explanation
* [ ] Debugging assistant
* [ ] Repository Q&A
* [ ] Code review
* [ ] Architecture analysis

## Phase 6 — Production

* [ ] Streaming responses
* [ ] Conversation management
* [ ] Authentication
* [ ] GitHub integration
* [ ] Deployment
* [ ] RAG evaluation
* [ ] Observability

---

# Learning Goals

This project is being developed to explore practical AI Engineering concepts including:

* LLM application architecture
* Prompt engineering
* Embeddings
* Vector databases
* Semantic search
* Retrieval-Augmented Generation
* Context management
* Repository-level code understanding
* AI tool calling
* Agentic workflows
* Full-stack AI application development

---

# License

This project is currently intended as a personal learning and portfolio project.
