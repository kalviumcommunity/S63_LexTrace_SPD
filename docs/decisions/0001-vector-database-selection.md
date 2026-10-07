# Architecture Decision Record (ADR) 0001: Vector Database Selection

## Status
Accepted (Planned for Week 3)

## Context
ChronoLex is a time-aware, source-grounded RAG application for banking regulatory compliance. The core requirement demands:
1. Fast local development and testability without complex multi-container orchestration.
2. Robust metadata filtering capabilities (filtering by effective date, expiration date, issuing authority, jurisdiction, and circular reference).
3. Seamless integration with Python-based chunking and retrieval pipelines.
4. Clean path to persistent local storage or remote cloud deployment.

## Options Considered

1. **ChromaDB (Selected for Development & Local Storage)**
   - *Pros*:
     - In-process / embedded mode with zero external service dependencies (runs in pure Python / SQLite).
     - Native metadata filtering on arbitrary keys (`$and`, `$gte`, `$lte` for date ranges).
     - Lightweight client-server Docker deployment option when containerizing for staging/production.
     - Minimal boilerplate for prototype and student/demonstration environments.
   - *Cons*:
     - Single-node scaling limits (sufficient for target regulatory corpus size of hundreds/thousands of documents).

2. **Qdrant**
   - *Pros*:
     - Excellent payload filtering and production-grade Rust performance.
     - Clean REST and gRPC Python SDK.
     - Has an in-memory/local mode (`:memory:` or local directory).
   - *Cons*:
     - Slightly higher initial configuration overhead than ChromaDB.

3. **PostgreSQL with pgvector**
   - *Pros*:
     - Combines relational tabular data with vector search.
     - ACID compliance and standard SQL joins.
   - *Cons*:
     - Requires running and maintaining a PostgreSQL server locally with extensions compiled/installed.
     - Overkill during early pipeline iteration (Week 1–2).

4. **Pinecone / Managed Cloud Services**
   - *Pros*:
     - Zero infrastructure management.
   - *Cons*:
     - Requires external API credentials, internet connectivity for tests, and incurs potential costs.
     - Violates zero-friction local developer experience.

## Decision
We select **ChromaDB** as the primary vector database for ChronoLex's retrieval foundation.
- For local development and automated CI tests, ChronoLex will use Chroma's embedded PersistentClient mode with local directory persistence.
- The retrieval interface will be modularized behind a repository/service interface (`VectorStoreService`) so that migrating to Qdrant or pgvector requires zero changes to the core RAG generation logic.

## Consequences
- No external vector database containers are required to begin working on embedding and retrieval pipelines.
- Vector data will be stored under a local data directory (e.g. `chroma_data/`), which is ignored in `.gitignore`.
- Date-based metadata filtering must map cleanly to ChromaDB where clauses (e.g., ISO-formatted date strings or unix timestamps).
