# Step 10.5 — Create the confirmed stories and move statuses — detail

1. **Create each confirmed story** (no-children cut, or a Step 7.5 split), born-split per the plans guide (`plans.guide`) §5:
   1. `createJiraIssue` with `parent=<epicKey>`, the type and the summary. Read the `key`.
   2. `Write` its content to `<plans.repo>/<board>/<KEY>.md`: front matter `jira/project/board/type/epic/summary`, plus the scope and acceptance, and its source Idea Board entry ids when it has any.
   3. Move it to **`<jira.createStatus>`** (step 2 below) when it is not already there.
   4. Run `python3 <plans.script> stub <KEY>`.

   5. When the story came from adopted Idea Board entries, `update` each source entry's `storyKey`.

   ⚡ Batch the `createJiraIssue` calls in one message. Batch the `stub` calls into one `Bash` call. The stub and the move are independent, so either order is fine. Do both for every story before Step 11.
2. **Move to `<jira.createStatus>`.** This covers every story just created, the epic if it is in Backlog, and the pre-existing Backlog stories the user did not keep parked. For each one, list its transitions with `<jira.mcpPrefix>executeRead(name="listJiraIssueTransitions", cloudId, inputs={issueIdOrKey: KEY}, responseFields=["transitions.id","transitions.name","transitions.to.name"])`, pick the transition whose target status (`to.name`) is `<jira.createStatus>`, and call `transitionJiraIssue(cloudId, issueIdOrKey=KEY, transitionId="<id>")`. Never reuse a transition id from another board: the same id can name a different transition on each board. ⚡ Batch the reads in one message and the transitions in the next.
3. **Verify** with one `board --jql 'key = <epicKey> OR parent = <epicKey>'` call. Nothing that was meant to move should still read Backlog. Report any that do in Step 13 as a line, not silently.
