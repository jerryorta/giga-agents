# 2.75d — Replace description + breadcrumb — detail

The description lives in the plans repo — replace it **there**, not in Jira (never `editJiraIssue(fields={description})`; Jira's description is only a stub). `Edit` the local plan file you read in Phase 1 (`$plan`, i.e. `<plans.repo>/<prefix>/<KEY>.md`): replace its **body** (everything below the front matter) with the revised description verbatim, preserving the `jira/project/board/type/epic/summary` front-matter block. You already read this file in Phase 1, so you have its current body to match against.

Then post a one-line breadcrumb comment so future readers know the description was re-validated (not modified by a human):

> *Pre-implementation re-validation (`/giga-workflow:jira`, <today's date>) — description revised against current code state. Original preserved in the plans-repo git history.*

Use `<jira.mcpPrefix>addOrEditJiraIssueComment(cloudId, issueIdOrKey, commentBody=<markdown>)` with a markdown body containing just that one paragraph.

Refresh the saved ticket details from Phase 1 (Step 5) with the revised description so Phase 3 plans against the up-to-date version.
