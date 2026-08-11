# AI Engineering Copilot

## Project Overview

AI Engineering Copilot is a full-stack AI developer assistant designed to understand and work with source-code repositories.

The system currently provides:

* Repository ingestion
* Source-code scanning
* Code chunking
* Content hashing
* Vector storage using ChromaDB
* Incremental ingestion
* Semantic code search
* Repository-aware AI chat
* FastAPI backend
* Next.js frontend
* Gemini LLM integration

The project is being developed incrementally toward a repository-aware AI coding assistant capable of code explanation, debugging, semantic search, and eventually AI tool-calling.

---

# 1. High-Level Architecture

```text
                    USER
                     |
                     v
              Next.js Frontend
                     |
                     v
              FastAPI Backend
                     |
          +----------+----------+
          |                     |
          v                     v
    Repository APIs          Chat API
          |                     |
          v                     v
 Repository Scanner          RAG Pipeline
          |                     |
          v                     v
      Code Chunking        Vector Search
          |                     |
          v                     v
      ChromaDB                Gemini
          |                     |
          +----------+----------+
                     |
                     v
                  Response
                     |
                     v
               Next.js UI
```

---

# 2. Current Project Structure

The backend currently follows a service-based architecture.

```text
backend/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── models/
│   │   └── code.py
│   │
│   ├── routes/
│   │   ├── chat.py
│   │   ├── ingestion.py
│   │   └── search.py
│   │
│   └── services/
│       │
│       ├── code_service.py
│       ├── repository_service.py
│       ├── search_service.py
│       ├── vector_store.py
│       │
│       └── llm/
│           └── llm_service.py
│
└── data/
    └── chroma/
```

The frontend is implemented separately using Next.js and TypeScript.

---

# 3. Core Technologies

| Technology | Purpose                             |
| ---------- | ----------------------------------- |
| Python     | Backend programming                 |
| FastAPI    | REST API framework                  |
| Next.js    | Frontend                            |
| TypeScript | Frontend development                |
| ChromaDB   | Vector database                     |
| Gemini     | LLM                                 |
| RAG        | Repository-aware question answering |
| Embeddings | Converting code/text into vectors   |
| Pydantic   | Data validation and models          |

---

# 4. Main Concept

The central idea of the project is:

```text
Repository
    |
    v
Read source files
    |
    v
Split code into chunks
    |
    v
Generate embeddings
    |
    v
Store chunks in vector database
    |
    v
User asks question
    |
    v
Convert question into embedding
    |
    v
Find similar code
    |
    v
Send relevant code to LLM
    |
    v
Generate repository-aware answer
```

This is called a Retrieval-Augmented Generation system.

---

# 5. Repository Ingestion

Repository ingestion is responsible for taking a local source-code repository and preparing it for semantic search.

The flow is:

```text
Repository Path
      |
      v
Scan Repository
      |
      v
Find supported source files
      |
      v
Read files
      |
      v
Split into chunks
      |
      v
Generate content hash
      |
      v
Check ChromaDB
      |
      +--------+--------+--------+
      |        |        |        |
     ADD    UPDATE    SKIP     DELETE
```

The DELETE stage handles files that were removed from the repository.

---

# 6. Repository Scanner

The repository scanner is responsible for discovering source files.

Instead of manually specifying every file, the application receives a repository path and scans it.

For example:

```text
project/
├── app/
│   ├── main.py
│   ├── routes/
│   │   └── chat.py
│   └── services/
│       └── llm_service.py
├── README.md
└── package.json
```

The scanner identifies the files that should be processed.

The purpose of separating this functionality into `repository_service.py` is to keep repository discovery independent from ingestion and vector storage.

---

# 7. Code Reading

The `read_file()` function reads the source file as text.

Conceptually:

```text
File Path
   |
   v
Path.read_text()
   |
   v
String containing source code
```

UTF-8 is used because most source code files use UTF-8 encoding.

Errors are ignored when reading files so that one malformed character does not immediately break the entire repository ingestion process.

---

# 8. Language Detection

The system determines the programming language from the file extension.

Example:

```text
.py     → Python
.js     → JavaScript
.ts     → TypeScript
.java   → Java
.cpp    → C++
.go     → Go
.rs     → Rust
```

This information is stored as metadata with each chunk.

This becomes useful later when constructing prompts for the LLM and displaying source information.

---

# 9. Code Chunking

Large source files should not be sent to the LLM as one giant piece of text.

Therefore we divide them into smaller chunks.

Currently the system uses a simple line-based chunking strategy.

For example:

```text
File:

1   import os
2   import json
3
4   def login():
5       ...
...
50  ...
```

With a chunk size of 50:

```text
Chunk 1 → lines 1-50
Chunk 2 → lines 51-100
Chunk 3 → lines 101-150
```

Each chunk becomes an independent searchable unit.

---

# 10. Why Chunking Is Important

Without chunking:

```text
Entire repository
      |
      v
Huge context
      |
      v
Expensive / inaccurate retrieval
```

With chunking:

```text
Repository
    |
    v
Small meaningful pieces
    |
    v
Vector search
    |
    v
Only relevant pieces
    |
    v
LLM
```

This allows the system to retrieve only the code relevant to a user's question.

---

# 11. CodeChunk Model

Each chunk contains information such as:

```text
repository_id
file_path
language
start_line
end_line
content
content_hash
```

Conceptually:

```python
CodeChunk(
    repository_id="abc123",
    file_path="app/auth.py",
    language="python",
    start_line=20,
    end_line=50,
    content="...",
    content_hash="..."
)
```

This is more useful than storing only the code.

We also know:

* where the code came from
* which repository it belongs to
* which language it uses
* which lines it represents
* whether it has changed

---

# 12. Content Hashing

Every chunk receives a SHA-256 hash.

Conceptually:

```text
Code Chunk
    |
    v
SHA-256
    |
    v
content_hash
```

For example:

```text
Original chunk
     |
     v
SHA-256
     |
     v
abc123...
```

If the code changes:

```text
Modified chunk
     |
     v
SHA-256
     |
     v
xyz789...
```

The hashes are different.

This allows us to determine whether a chunk actually changed.

---

# 13. Why Content Hashing Is Important

Without hashing, every ingestion would potentially reprocess everything.

Example:

```text
180 chunks

Ingest
 ↓
180 embeddings

Ingest again
 ↓
180 embeddings again
```

This is inefficient.

With hashing:

```text
180 chunks

First ingestion:
180 ADD

Second ingestion:
180 SKIP

One file changes:

179 SKIP
1 UPDATE
```

This is called incremental ingestion.

---

# 14. Repository ID

Every repository receives a deterministic ID based on its path.

Conceptually:

```text
Repository Path
      |
      v
SHA-256
      |
      v
Repository ID
```

This allows multiple repositories to exist in the same vector database while keeping their data logically separated.

For example:

```text
Repository A
repository_id = abc123

Repository B
repository_id = xyz789
```

Search can then be restricted to one repository.

---

# 15. ChromaDB

ChromaDB is being used as our vector database.

It stores:

```text
ID
Document
Embedding
Metadata
```

Our metadata contains information such as:

```text
repository_id
file_path
language
start_line
end_line
content_hash
```

The actual source code is stored as the document.

---

# 16. Incremental Ingestion

Our ingestion system currently supports:

```text
ADD
UPDATE
SKIP
DELETE
```

### ADD

If a chunk doesn't exist:

```text
ChromaDB
   |
   └── chunk doesn't exist
             |
             v
            ADD
```

### UPDATE

If the chunk exists but the hash changed:

```text
Existing chunk
      |
      v
Compare hash
      |
      v
Different
      |
      v
UPDATE
```

### SKIP

If the chunk exists and the hash is identical:

```text
Existing chunk
      |
      v
Compare hash
      |
      v
Same
      |
      v
SKIP
```

### DELETE

If a previously indexed file no longer exists in the repository:

```text
Indexed file
     |
     v
Not present in repository
     |
     v
DELETE vectors
```

---

# 17. Ingestion Endpoint

Endpoint:

```text
POST /api/repository/ingest
```

Purpose:

```text
Take repository path
       |
       v
Scan repository
       |
       v
Read files
       |
       v
Chunk code
       |
       v
Hash chunks
       |
       v
Synchronize ChromaDB
```

Input:

```text
repository_path
```

Example conceptually:

```text
/api/repository/ingest?repository_path=C:/projects/my-app
```

Response contains information such as:

```json
{
    "repository": "...",
    "repository_id": "...",
    "file_count": 20,
    "chunk_count": 180,
    "ingestion": {
        "added": 0,
        "updated": 1,
        "skipped": 179,
        "deleted": 0
    }
}
```

This response is useful because it tells us exactly what happened during ingestion.

---

# 18. Semantic Code Search

Once the repository is ingested, we can search it semantically.

Traditional search works like:

```text
"authentication"
       |
       v
Find exact word
```

Semantic search works differently:

```text
"How does the application authenticate users?"
                 |
                 v
             Embedding
                 |
                 v
        Vector similarity
                 |
                 v
Relevant code chunks
```

This means the query doesn't necessarily need to contain the exact words present in the source code.

---

# 19. Search Service

The `search_service.py` contains:

```text
search_code()
```

It accepts:

```text
query
repository_id
limit
```

The logic is:

```text
User query
     |
     v
ChromaDB query
     |
     v
Filter by repository_id
     |
     v
Find nearest code chunks
     |
     v
Return structured results
```

---

# 20. Search Endpoint

Endpoint:

```text
GET /api/search
```

Parameters:

```text
query
repository_id
limit
```

Example:

```text
/api/search?query=authentication&repository_id=abc123&limit=5
```

The endpoint calls:

```text
search_code()
```

which queries ChromaDB.

---

# 21. Why Repository ID Is Required

Suppose ChromaDB contains:

```text
Repository A
    auth.py

Repository B
    auth.py
```

A search for:

```text
authentication
```

could potentially return code from both repositories.

We don't want that.

Therefore:

```text
query
+
repository_id
```

means:

> Search for this concept, but only inside this repository.

---

# 22. CodeSearchResult

Instead of returning ChromaDB's raw response, we transform it into a structured model.

Conceptually:

```python
CodeSearchResult(
    content="...",
    file_path="app/auth.py",
    language="python",
    start_line=20,
    end_line=45,
    score=0.21
)
```

This creates a clean boundary between:

```text
ChromaDB
```

and:

```text
Application logic
```

The rest of the application doesn't need to understand ChromaDB's raw response format.

---

# 23. Search Flow

The complete search flow is:

```text
GET /api/search
        |
        v
search route
        |
        v
search_code()
        |
        v
ChromaDB
        |
        v
Vector similarity search
        |
        v
Retrieve documents + metadata
        |
        v
CodeSearchResult[]
        |
        v
API response
```

---

# 24. AI Chat

The chat system is the first direct connection to the LLM.

The basic flow currently is:

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
Response
 |
 v
Next.js
```

The LLM service is responsible for communicating with Gemini.

---

# 25. LLM Service

The LLM service abstracts the Gemini API from the rest of the application.

Instead of putting Gemini API calls directly inside the route:

```text
chat.py
   |
   └── Gemini API
```

we use:

```text
chat.py
   |
   v
llm_service.py
   |
   v
Gemini API
```

This is better separation of responsibility.

The route handles HTTP.

The LLM service handles AI communication.

---

# 26. Chat Endpoint

Endpoint:

```text
POST /api/chat
```

The request contains a user message.

The current basic flow is:

```text
User message
     |
     v
chat route
     |
     v
generate_response()
     |
     v
Gemini
     |
     v
Generated answer
```

The response is returned to the frontend.

---

# 27. Current RAG Status

This distinction is important for interviews.

We have built the infrastructure required for RAG:

```text
Repository
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Store
    ↓
Semantic Search
```

We have also built the LLM layer:

```text
User
 ↓
Gemini
 ↓
Response
```

The next step is to fully connect them:

```text
User question
      |
      v
Semantic Search
      |
      v
Relevant Code
      |
      v
Context Builder
      |
      v
Prompt
      |
      v
Gemini
      |
      v
Repository-aware answer
```

This is the important transition from a basic LLM chatbot to an actual RAG-powered developer assistant.

---

# 28. Source Attribution

We have already prepared the data needed for source attribution.

Every retrieved result knows:

```text
file_path
start_line
end_line
language
content
```

Therefore the final response can eventually show:

```text
Answer:
The authentication logic is handled by...

Sources:

app/services/auth_service.py
Lines 20-45

app/routes/auth.py
Lines 10-30
```

This is especially important for developer tools because developers need to verify AI-generated answers.

---

# 29. Frontend

The frontend is implemented using Next.js and TypeScript.

Its current responsibility is:

```text
User Interface
     |
     v
User enters question
     |
     v
API request
     |
     v
FastAPI
     |
     v
AI response
     |
     v
Display response
```

The frontend communicates with the Python backend instead of directly communicating with Gemini.

This keeps the API key and AI orchestration logic on the backend.

---

# 30. Why We Use FastAPI + Next.js

The architecture separates frontend and backend responsibilities.

### Next.js

Responsible for:

* UI
* User interaction
* Chat interface
* Displaying responses
* Future source/file panels
* Conversation interface

### FastAPI

Responsible for:

* Repository ingestion
* Code processing
* Vector search
* RAG
* LLM communication
* AI orchestration
* Backend business logic

This is a standard full-stack architecture.

---

# 31. Current Endpoints

## POST `/api/chat`

Purpose:

```text
Send user question to the AI
```

Flow:

```text
Frontend
   ↓
POST /api/chat
   ↓
chat.py
   ↓
llm_service.py
   ↓
Gemini
   ↓
Response
```

Current status:

Complete basic implementation.

Next improvement:

Connect it with RAG.

---

## POST `/api/repository/ingest`

Purpose:

```text
Index a repository into ChromaDB
```

Flow:

```text
Repository path
      ↓
Repository scanner
      ↓
Read files
      ↓
Chunk code
      ↓
Hash chunks
      ↓
ChromaDB
      ↓
ADD / UPDATE / SKIP / DELETE
```

Current status:

Working.

---

## GET `/api/search`

Purpose:

```text
Search repository code semantically
```

Flow:

```text
Query
  +
Repository ID
      ↓
search_code()
      ↓
ChromaDB
      ↓
Similarity search
      ↓
CodeSearchResult[]
```

Current status:

Working.

---

# 32. Complete Current System Flow

At this point, the system can be understood as two connected pipelines.

## Pipeline 1 — Knowledge Preparation

```text
Repository
    |
    v
Scanner
    |
    v
Files
    |
    v
Code Reader
    |
    v
Chunker
    |
    v
Content Hash
    |
    v
ChromaDB
```

With synchronization:

```text
ADD
UPDATE
SKIP
DELETE
```

---

## Pipeline 2 — Knowledge Retrieval

```text
User Query
     |
     v
Search API
     |
     v
Semantic Search
     |
     v
ChromaDB
     |
     v
Relevant CodeSearchResult[]
```

---

## Future Pipeline 3 — RAG Generation

This is what we are building next:

```text
User Question
      |
      v
Semantic Search
      |
      v
Relevant Code
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
Answer
      |
      +-------> Sources
```

---

# 33. What We Have Learned Technically

This project has already covered several important AI engineering concepts:

### Backend Engineering

* FastAPI
* REST APIs
* Routing
* Service separation
* Pydantic models
* Error handling
* Repository processing

### AI Engineering

* LLM APIs
* Embeddings
* Vector databases
* Semantic search
* RAG architecture
* Context retrieval

### Data Engineering

* Chunking
* Hashing
* Incremental processing
* ADD / UPDATE / SKIP / DELETE synchronization
* Metadata management

### Full Stack

```text
Next.js
   ↓
FastAPI
   ↓
Python Services
   ↓
ChromaDB
   ↓
Gemini
```

---

# 34. What Is Still Left

The major remaining pieces are:

```text
CURRENT
   |
   ├── Repository ingestion       DONE
   ├── Code chunking              DONE
   ├── Content hashing            DONE
   ├── Incremental ingestion      DONE
   ├── ChromaDB                   DONE
   ├── Semantic search             DONE
   ├── Search API                  DONE
   ├── Basic Gemini integration    DONE
   └── Basic frontend              DONE
            |
            v
NEXT
   |
   ├── RAG context builder
   ├── Source-aware prompts
   ├── Chat + retrieval integration
   ├── Source attribution in UI
   ├── Conversation history
   ├── Streaming responses
   ├── Repository/file selection
   ├── Debugging workflow
   ├── Code explanation workflow
   └── AI tool calling
```

---

# 35. Interview Explanation

If an interviewer asks:

> "Explain your AI Engineering Copilot."

A simple explanation is:

> "I built a full-stack AI developer assistant where the backend is implemented using FastAPI and the frontend uses Next.js. The system can ingest a source-code repository, scan and chunk the code, generate embeddings, and store the chunks with metadata in ChromaDB. I implemented semantic code search using vector similarity and repository-level filtering. To make ingestion efficient, I added content hashing so unchanged chunks are skipped while modified chunks are updated and new or deleted files are synchronized. The next layer is RAG, where retrieved code chunks are converted into contextual prompts for the LLM so that responses are grounded in the actual repository and can provide source-level attribution."

That is a much stronger explanation than simply saying:

> "I built a chatbot using Gemini."

---

# 36. The Most Important Architecture Principle

Each component has one primary responsibility:

```text
repository_service
        ↓
Find files

code_service
        ↓
Read and chunk code

vector_store
        ↓
Store and retrieve vectors

search_service
        ↓
Perform semantic search

llm_service
        ↓
Communicate with Gemini

routes
        ↓
Expose APIs

Next.js
        ↓
Provide user interface
```

This separation makes the application easier to:

* test
* debug
* maintain
* extend
* explain during interviews

---

# 37. Current Architecture in One Diagram

```text
                       NEXT.JS
                          |
             +------------+------------+
             |                         |
             |                         |
             v                         v
        /api/chat              /api/search
             |                         |
             v                         v
        chat.py                 search.py
             |                         |
             v                         v
       llm_service              search_service
             |                         |
             v                         v
          Gemini                  ChromaDB
                                       ^
                                       |
                                  vector_store
                                       ^
                                       |
                                  ingestion.py
                                       ^
                                       |
                              repository_service
                                       |
                                       v
                                  Repository
                                       |
                                       v
                                  code_service
                                       |
                                       v
                              Code Chunks + Hash

