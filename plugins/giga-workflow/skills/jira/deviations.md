# 5d: Document deviations from the ticket — detail

After fixes are applied, compare the final implementation against the original ticket AC and specs. If **anything was intentionally built differently** — due to architectural constraints, a better approach discovered during development, a spec ambiguity resolved a certain way, or a scope reduction — post a comment on the Jira ticket documenting it.

Use `<jira.mcpPrefix>addOrEditJiraIssueComment` with a markdown comment structured as:

```
## Implementation Notes

### Deviations from Spec
- **<AC item or spec section>** — Originally specified as X. Implemented as Y instead.
  *Reason:* <brief architectural/technical rationale>

### Decisions Made
- <Any ambiguity in the ticket that was resolved during development, and how>
```

**When to post this comment:**
- A guard, component, or route was structured differently than the ticket described
- A specified behavior was simplified, deferred, or replaced with a stub
- An AC item was partially implemented (note what's covered and what isn't)
- An architectural pattern was chosen that differs from any example in the ticket

**When to skip it:**
- The implementation matches the ticket exactly with no notable deviations

This comment becomes the authoritative record of why the code diverged from the spec, visible to future developers and the PM without needing to trace git history.
