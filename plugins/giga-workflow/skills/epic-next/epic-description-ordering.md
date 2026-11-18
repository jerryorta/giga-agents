# Step 5 — Read the tracker epic description — detail

```
python3 <plans.script> section <config.epicKey> Wave
```

This prints only the epic's wave sections (`## Wave Plan` / `## Waves` / `## Wave order` with their `### Wave N` subsections), not the whole file, whose `## Shipped` and decision history can be several times longer. The epic plan file is the source of truth for ordering once epics are stubbed. Parse the output to extract the **ordered list of story keys** in the sequence they appear, top to bottom, preserving any section groupings (waves, tracks, etc.) as the `config.groupLabel` for each story. If it exits 1 (no `Wave` heading: the epic uses another shape), `Read` the path it names on stderr instead.
