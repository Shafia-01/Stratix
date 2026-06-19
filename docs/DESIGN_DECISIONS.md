# Stratix Engineering Design Decisions Log

This document serves as the official design log of key architectural decisions and engineering trade-offs accepted during the development of Stratix.

---

### SQLite + WAL over PostgreSQL
**Context:** The application requires a relational database to store execution states, keywords, metrics, evaluation reports, and monitoring schedules while maintaining trivial local and containerized deployments.
**Decision:** We chose SQLite configured with Write-Ahead Logging (WAL) and SQLAlchemy connection pools.
**Alternatives considered:** We considered deploying PostgreSQL as a containerized service. While PostgreSQL scales better under highly concurrent workloads, it introduces infrastructure management overhead, network latency, and configuration complexity for single-node setups. SQLite in WAL mode allows simultaneous reads and non-blocking writes which satisfies the single-node concurrency requirements.
**Trade-offs accepted:** We accept SQLite's single-writer limitation. We mitigate connection locking contention under concurrent tool writes by registering the sqlite connection pragmas `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` via SQLAlchemy event listeners to auto-retry blocked operations for up to 5 seconds.

### APScheduler + SQLAlchemy jobstore over Celery + Redis
**Context:** The platform runs recurring keyword research jobs at user-defined intervals that must survive backend process restarts.
**Decision:** We chose APScheduler (via `BackgroundScheduler`) backed by an SQLite `SQLAlchemyJobStore`.
**Alternatives considered:** We considered a Celery and Redis stack for task queuing and scheduling. While Celery offers robust distributed execution guarantees and multi-worker pools, it requires setting up and maintaining external message brokers and separate worker processes. APScheduler runs directly inside the FastAPI application thread pool, persisting execution intervals within the shared SQLite database.
**Trade-offs accepted:** We sacrifice the safety of out-of-process distributed job execution and horizontal worker scaling. If the main FastAPI service fails or is restarted, jobs cannot execute until the container/process recovers, although state persistence in the database ensures scheduling resumes correctly upon boot.

### LangGraph's native checkpointing over a custom state machine
**Context:** Stateful agent execution tracks long-running research loops that must pause at intermediate stages for human-in-the-loop (HITL) plan and report reviews.
**Decision:** We chose LangGraph's native compile-time state checkpointing and `SqliteSaver` checkpointer.
**Alternatives considered:** We considered writing a custom state machine logic using database-backed JSON blobs and manual session routing. However, writing custom resume/interrupt serialization, tracking execution histories, and restoring execution context manually is highly error-prone. LangGraph's native `interrupt()` pattern natively handles yields, pauses, and updates to the active threads.
**Trade-offs accepted:** We depend strictly on LangGraph's framework design, meaning our state schemas must align with its TypedDict format and execution structures. Changes to the underlying state machine require refactoring graph node registration code and migrations of checkpointed tables.

### In-memory Prometheus-style metrics over a full Prometheus + Grafana stack
**Context:** Operational latency, model token consumption, and execution results need to be monitored in real-time.
**Decision:** We chose an in-memory thread-safe metrics collector (`KeylyticsMetrics`) exposed via a standard `/metrics` text endpoint.
**Alternatives considered:** We considered integrating standard Prometheus client libraries and configuring dedicated Prometheus and Grafana containers. This stack would be ideal for production but introduces additional container orchestration overhead and complexity for small deployments. An in-memory collector provides immediate Prometheus compatibility without any external dependencies.
**Trade-offs accepted:** The in-process metrics are not persisted and do not survive application restarts. Furthermore, this approach does not scale beyond a single application process, meaning metrics cannot be aggregated if the API tier is scaled horizontally.

### LLM-as-judge evaluation over static test assertions for agent quality
**Context:** Evaluating the open-ended text quality of research plans and generated strategy reports cannot be verified using deterministic assertions.
**Decision:** We chose Gemini-based LLM-as-judge evaluators running at `temperature=0.0`.
**Alternatives considered:** We considered using standard assertions (e.g., checking word counts, keyword existence, or structural markdown formats). While cheap and fast, these checks fail to assess qualitative metrics such as objectives coverage, recommendation coherence, or semantic focus. The LLM judge provides multi-dimensional quality grades based on structured scoring rubrics.
**Trade-offs accepted:** We accept the cost and latency of running additional LLM queries during the finalization stage of a research run. To mitigate judge non-determinism, we pin the evaluation temperature to `0.0` and fallback models, though we currently accept the risk of rating drift without judge-of-judge validation.

### Tenacity retries scoped to specific exception types, never bare Exception
**Context:** Upstream API integrations (e.g., DataForSEO, Google Trends, Gemini) are prone to transient network drops and rate limits.
**Decision:** We chose Tenacity retry decorators configured with explicit exception targets (`KeylyticsAPIError`, `requests.exceptions.RequestException`).
**Alternatives considered:** We considered blanket try-except blocks or general retry decorators targeting base `Exception`. However, retrying general exceptions masks programming errors (such as `AttributeError`, `KeyError`, or `ValueError`), leading to infinite loops and delaying discovery of bugs. Scoping retries to recoverable network exceptions ensures program bugs crash immediately.
**Trade-offs accepted:** If an API client encounters an unhandled exception type that does not inherit from targeted classes, the retry mechanism will not trigger, resulting in an immediate execution failure.

### Multi-model Gemini fallback chain over a single pinned model
**Context:** API rate limits, transient provider issues, or model deprecations can break the agent graph execution midway.
**Decision:** We chose a hierarchical model fallback chain (`gemma-4-31b-it`, `gemma-4-26b-a4b-it`, `gemini-3.1-flash-lite`, etc.) utilizing LangChain's `with_fallbacks()` mechanism.
**Alternatives considered:** We considered pinning all LLM calls to a single, high-performing model to ensure output formatting consistency. However, this leaves the application vulnerable to immediate failures if the primary model hits quota exhaustion. A cascading fallback list increases execution reliability.
**Trade-offs accepted:** We accept variance in response time and formatting accuracy when execution falls through to smaller models in the chain. We mitigate this by defining structured output schemas to force smaller models to adhere to required JSON shapes.

### DataForSEO sandbox/credit-preservation auto-switching over always using the live API
**Context:** Third-party keyword data queries deplete live API credits rapidly during active local development, testing, and system demos.
**Decision:** We chose a credit-preservation client that checks user balances and auto-switches requests to sandbox endpoints if settings like `DATAFORSEO_DEMO_MODE` or low balance thresholds are met.
**Alternatives considered:** We considered mocking keyword responses locally using static files. However, static mocks do not test the actual network clients or endpoint serialization logic. Auto-switching to the sandbox verifies the API parser flow using mock data payloads without depleting active credits.
**Trade-offs accepted:** Sandbox data is synthetic and less accurate than live search queries, which can degrade the quality of generated strategy reports during development runs. We accept this trade-off to avoid unmanaged credit depletion.

### Separate Docker images for FastAPI and Streamlit over a single monolithic container
**Context:** The system consists of an API backend and a Streamlit dashboard that share a database volume.
**Decision:** We chose separate Dockerfiles (`Dockerfile.fastapi`, `Dockerfile.streamlit`) coordinated via Docker Compose.
**Alternatives considered:** We considered running both services inside a single Docker image using a process manager like Supervisord. Although a single image simplifies container orchestration, it violates single-responsibility design, inflates build times, and prevents independent scaling or process restarts.
**Trade-offs accepted:** Coordinated deployments require maintaining two separate Dockerfiles. Developers must configure shared Docker volumes to expose the SQLite database file across the container boundaries.

### Quality gate (deterministic) before critic node (LLM-based) rather than either alone
**Context:** The agent pipeline must validate data quality before generating strategy reports, preventing low-quality findings from polluting the recommendations.
**Decision:** We chose a deterministic quality check (`quality_gate_node`) that runs before the LLM-based `critic_node`.
**Alternatives considered:** We considered using only an LLM critic to check data quality, or using only a deterministic gate. An LLM critic alone is expensive and can fail to identify simple count discrepancies, whereas a deterministic gate alone cannot evaluate semantic consistency. Running the cheap deterministic gate first allows the system to fail fast and loop back before calling the LLM.
**Trade-offs accepted:** This adds an additional step and router check to the LangGraph execution cycle. We accept this small graph complexity in exchange for reduced LLM call costs and faster recovery loops.

---

## What We'd Do Differently at Scale

If Stratix were scaled to support enterprise-grade concurrent tenants, the following structural limitations of the current architecture would need to be addressed:

* **Database Scale Limitation**: SQLite's single-writer ceiling would eventually cause database lock exceptions under high concurrency. We would replace it with PostgreSQL to support high concurrent-write scaling.
* **State Checkpointer Redundancy**: The current `SqliteSaver` checkpointer relies on local SQLite locking. At scale, we would migrate to a distributed checkpointer (such as PostgreSQL or Redis savers) to allow checkpointer state replication across container boundaries.
* **Distributed Monitoring Scheduler**: APScheduler's local thread pool execution would be replaced by an out-of-process distributed queue system (such as Celery backed by Redis or RabbitMQ) to guarantee job distribution and prevent scheduler failure from blocking the entire API gateway.
* **Distributed Metrics Accumulation**: In-memory metrics collections would be replaced by the official Prometheus client library pushed to a centralized Pushgateway or pulled by Prometheus scraping agents, enabling tracking across horizontally scaled replicas.
