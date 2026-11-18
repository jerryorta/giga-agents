# Step 2 — Seeding a new board from `boardTemplate` — detail

When `boardTemplate` names a file that exists, seed the new config from it instead: load that file as the **base config**, drop every key that starts with `_`, and hold their text as `templateNotes` for the Step 9 gate (`baseFromTemplate = true`). Step 12 still writes `name`, `epicKey`, `jql`, `completionMessage` and the other epic-specific fields from this epic.
