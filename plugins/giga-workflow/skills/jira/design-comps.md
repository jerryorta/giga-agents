# Phase 2.5: Fetch Design Comps — detail

Before planning, extract any design references from the ticket and load the comp content so it informs the implementation plan.

### Detect design references

Scan the ticket description and comments for:

- **Stitch links** — any mention of a Stitch project/screen ID or URL (a Stitch URL, `stitch project`, a `projectId` / `screenId`)
- **Figma links** — any `figma.com/file/...` or `figma.com/design/...` URL

### Fetch Stitch comps (if found)

Only when the Stitch MCP tools are available in the session; otherwise report the reference to the user and continue.

1. Load the project overview:
   ```
   mcp__stitch__get_project(projectId)
   ```
2. List all screens:
   ```
   mcp__stitch__list_screens(projectId)
   ```
3. For each screen referenced in the ticket (or all screens if the ticket says "all"), fetch the full screen spec:
   ```
   mcp__stitch__get_screen(projectId, screenId)
   ```
4. **Summarize the comps** — layout, component names used, color tokens, spacing, typography, interactive states. Keep this summary concise; it will be passed into the planning context.

### Fetch Figma comps (if found)

Use `WebFetch` to retrieve the Figma embed URL or use the Figma share URL directly if it is publicly accessible. Capture the design description, component names, and any annotated specs visible from the URL. If the link requires auth (returns a login page), report to the user:

> "Figma link found but requires authentication — please paste the relevant comp screenshot or description."

Then wait for the user to supply it before proceeding.

### No design reference

If the ticket contains no Stitch or Figma reference, skip this phase and proceed to Phase 2.75.
