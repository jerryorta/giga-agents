# 7b — Dependency-driven path (for backend / foundation epics) — detail

For **each story**, read its description and extract:

1. **Explicit dependencies** — match patterns like `depends on ABC-XXX`, `blocked by ABC-XXX`, `prerequisite: ABC-XXX`. Build a directed edge from the dependency to this story.
2. **Implicit dependencies** — if a story description names a piece of infrastructure another story is building (e.g., "uses the `events` table from ABC-253"), add an edge from the building story to this consumer.
3. **Sibling conflict** — same as route-driven (two stories touching the same file = sequential within a wave).

Then build a **directed acyclic graph** (DAG) of stories. Topological depth (longest path from any root) becomes the wave assignment:
- Stories with no incoming edges → Wave 1
- Stories whose dependencies are all in Wave N → Wave N+1
- Cycles flagged as errors (must resolve before continuing).
