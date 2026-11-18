# Step 7.5 — Split multi-layer stories, backend first — detail

**The backend story** carries the functions, rules, indexes, seed, and the models / API contract the
frontend codes against. It is **always first**: every frontend story from the split depends on it (an
edge in the 7b DAG; ahead of them in a sequential wave on the route-driven path).

**The frontend story or stories** follow — one per layer (store vs UI) when each stands alone — and,
once the backend story has merged, run in parallel (separate clones / sessions).

Why: one multi-layer story runs its layers serially in one session whose context only grows; split, each
layer is its own session and the frontend layers run in parallel.

Skip the split only when the frontend change is a thin consumer of the backend change (a handful of
files) — say so in Step 9.

Proposed splits are presented in Step 9 and minted by Step 10.5 only after the user confirms, before Step
11 writes the wave plan; the original ticket becomes the backend story.
