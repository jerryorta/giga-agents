# Step 7 — No To Do stories — detail

If **no stories are in "To Do"**: report `config.completionMessage`. Then count the epic's open children with
`python3 <plans.script> board --jql 'parent = <config.epicKey> AND statusCategory != Done'`. If the result is `[]`, the epic is
finished: invoke the skill named in `epicCloseSkill` as `closed <config.epicKey>` (absent: skip this hand-off) and print its block, whose `Plan next` names the epic to
`/giga-workflow:epic-plan`, then `Review: /giga-workflow:epic-review <config.epicKey> — before /giga-workflow:epic-plan <NEXT-KEY>`. Stop either way.
