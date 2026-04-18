# Architecture Decision Document

## Problem statement
The project needs a practical AI assistant that can ingest a GitHub repository, analyze architecture signals, and generate a structured architecture review that is demo-friendly and easy to run.

## Why agentic design was chosen
An agentic pipeline was selected to separate concerns between evidence collection and architectural judgment. This keeps the workflow explainable and makes each stage testable independently.

## Why 2+ agents were used
- **Repository Analysis Agent** focuses on fact collection (metadata, files, dependencies, structure signals).
- **Architecture Review Agent** focuses on interpretation (risks, anti-patterns, recommendations).
- **Report Writer Agent ** converts outputs into polished markdown.

This division improves traceability: the second agent can be audited against first-agent evidence.

## Why memory was added
Memory supports iterative architecture reviews:
- stores previous analyses keyed by `owner/repo`
- stores timeline history of runs for trend view
- remembers user preferences (focus, with report depth defaulting to deep)
- performs architecture drift detection between consecutive runs
- tracks change metrics (`risk_delta`, `module_delta`, `dependency_delta`, `stack_changed`, file changes, architecture-level changes)
- computes drift summary (`drift_status`, `improvement_score`)

This enables re-analysis demos and longitudinal architecture tracking.

## ReAct loop decision
The repository analysis stage uses an explicit bounded ReAct-style loop:
- **Thought**: determine next missing evidence
- **Action**: execute a concrete tool call
- **Observation**: capture and summarize the result
- repeat until evidence is sufficient or guardrails trigger stop

Guardrails:
- max iterations (`MAX_REACT_ITERATIONS`, default 8)
- stop conditions: `enough_evidence`, `api_error`, `rate_limit`, `max_iterations`
- fallback mode to continue with partial evidence when a stop condition occurs early

This decision was made to improve traceability and make tool-driven reasoning visible for evaluation.

## Why tool-calling was used
Tool-calling gives deterministic access to operational functions:
- `fetch_repo_metadata`
- `list_repo_files`
- `read_repo_file`
- `detect_tech_stack`
- `parse_dependencies`
- `analyze_project_structure`
- `store_analysis_memory`
- `retrieve_analysis_memory`
- `generate_architecture_report`

Using LangChain tool wrappers provides standardized interfaces and easier future extension.

## Observability and evaluation visibility
To improve explainability and rubric alignment:
- ReAct step traces are persisted in each analysis result
- Streamlit exposes progress stages, metrics cards, and tabs including **Reasoning Trace**, **Architecture Drift**, **Action Plan**, and **Reports**
- CLI prints ReAct summary and recent reasoning steps
- markdown report includes a ReAct trace section

## Standout features added
- **Drift Timeline**: uses run history to chart risk/module/dependency trends across analyses for the same repo.
- **Prioritized Action Plan**: converts recommendations into execution items with `priority`, `owner_role`, `effort`, `impact`, and `due_window`.

## LLM choice considerations
OpenAI was selected as the default because:
- simple integration with `langchain-openai`
- strong structured reasoning for architecture summaries
- predictable developer experience for prototypes

Design keeps provider abstraction (`LLM_PROVIDER`) so Claude can be added later with minimal orchestration changes.

## GitHub API usage decisions
- GitHub REST API is used for repo metadata, tree listing, and file content retrieval.
- Optional token allows private-repo support and improved rate-limit headroom.
- File ingestion is constrained by file count and size limits to reduce token explosion.

## Streamlit vs CLI decision
Both were implemented:
- **Streamlit (preferred)** for visual demo and report download
- **CLI** for automation and quick terminal usage

This dual interface improves submission and reviewer usability.

## Trade-offs and limitations
- Heuristic structure analysis can miss implicit architecture conventions.
- Large repositories are sampled, so deep context can be incomplete.
- LLM output variability is managed with fallback logic but not fully deterministic.
- Dependency parsing focuses on common manifests, not every ecosystem nuance.
- Drift scoring is heuristic and intended as directional guidance, not a formal maturity index.
- JSON memory is lightweight and simple, but less powerful than DB/vector-backed retrieval for large histories.

## Future enhancements
- Add async file retrieval and batching
- Add repository diff mode across commits/tags
- Integrate additional analyzers (security scanners, complexity metrics)
- Add eval suite with golden reports
- Add Anthropic provider implementation and model routing
