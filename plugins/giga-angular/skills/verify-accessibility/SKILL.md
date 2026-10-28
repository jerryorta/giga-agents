---
name: verify-accessibility
description: >-
  Verify and auto-fix accessible names (aria-label) and test ids (data-testid) in Angular templates so Playwright can reach them by role and name. Native elements, CDK triggers and icon-only buttons get a name from the icon and its context; structural containers get a test id. Per-library rules come from the repo's config and win over the generic ones. Use when the user says "verify accessibility", "add aria labels", "check the selectors", or names a template or directory. Args: a file or directory ($ARGUMENTS).
---

# Verify and AUTO-FIX accessibility selectors

Verify and AUTO-FIX accessibility selectors for: $ARGUMENTS

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `angular`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `accessibility.standards` | `[{ "doc": "<path>", "match": ["<glob>", ...] }]`: rule docs. An entry without `match` applies to every file; an entry with `match` applies to files under those path globs. Where a doc and this skill differ, the doc wins | only the generic rules below apply |

## Phase 1: Analysis

1. Determine the target:
   - If `$ARGUMENTS` is an HTML file, analyze that file
   - If `$ARGUMENTS` is a `.ts` component file, find and analyze its associated `.html` template
   - If `$ARGUMENTS` is a directory, find all `*.component.html` files recursively
2. For each template, collect the `accessibility.standards` entries that apply: every entry with no `match`, and every entry whose `match` covers the template's path (relative to the repository root). Read each doc. Rules from a path-matched doc override the generic rules below for that file, including where the accessible name goes (an input, an attribute, a bound label).
3. Check which kind of element the file uses before reporting: native elements, `@angular/cdk` directives, or a component from a design library. A design-library component takes its name through whatever its doc says; with no doc for it, treat it as unknown and report rather than fix.
4. For each template, identify:

### Missing `aria-label` (interactive elements)

**Native elements and CDK:**

- **Icon-only buttons**: a native `<button>` whose only child is an icon glyph (an inline SVG or an icon-font ligature span) and no visible text
- **Overlay triggers**: icon-only buttons with `cdkOverlayOrigin` or `cdkMenuTriggerFor` that lack `aria-label`
- **Inputs without labels**: `<input>` elements with no `<label for>` and no `aria-label`

**Design-library components:** the rules come from the matched docs. A `placeholder` is never an accessible name.

Skip elements that already carry `aria-label`, `[aria-label]`, `[attr.aria-label]`, or the name input a matched doc defines.

### Missing `data-testid` (structural containers)

- **Top-level wrapper divs**: the outermost `<div>` with a component-specific class (for example `class="lead-list-container"`)
- **Form containers**: `<form>` elements
- **Sidenav and drawer containers**: the root element of a side panel or drawer
- **Dialog content wrappers**: root divs in dialog templates
- **List and table wrappers**: container divs around a `<table>` or a list component

Skip elements that already have `data-testid`. A matched doc that bans or limits test ids (for example per-row ids) wins.

## Phase 2: Auto-Fix (safe changes)

After analysis, apply these fixes without asking.

### Always auto-fix

- **Icon-only buttons with a clear purpose**: add `aria-label` from the icon name and the surrounding context:
  - `close` icon: `aria-label="Close [context]"` (for example "Close dialog", "Close preview")
  - `delete` icon: `aria-label="Delete [context]"`
  - `edit` icon: `aria-label="Edit [context]"`
  - `download` icon: `aria-label="Download [context]"`
  - `save` icon: `aria-label="Save [context]"`
  - `add` and `remove` icons: `aria-label="Zoom in"` and `"Zoom out"`, or the contextual equivalent
  - `undo` and `redo` icons: `aria-label="Undo [context]"` and `"Redo [context]"`
  - `filter_list` icon: `aria-label="Toggle filter menu"`
  - `arrow_back` icon: `aria-label="Go back"` or `"Back to [context]"`
  - `visibility` icon: `aria-label="View [context]"`
  - `archive` icon: `aria-label="Archive [context]"`
  - `content_copy` icon: `aria-label="Copy [context]"`
  - `search` icon: `aria-label="Search [context]"`
  - Where a matched doc gives its own icon-to-name table, use that table, written the way the doc says
- **Button toggle groups**: add `aria-label` from the options (for example "Filter by file type")
- **Missing `data-testid` on structural containers**: add one from the element's class name or component context, in kebab-case
- **Tooltips**: if the element already carries a tooltip attribute, use its text as the `aria-label` value

### Do NOT auto-fix (report only)

- Elements where the correct label text is ambiguous (several plausible labels)
- Dynamic contexts where a static `aria-label` would be wrong (suggest the `[attr.aria-label]` pattern)
- Elements inside `@for` loops where the label should include item-specific context
- Design-library elements with no matched doc

## Phase 3: Report

After applying fixes, output this summary.

```
## Accessibility Verification: [filename or directory]

### Files Analyzed
- [every HTML file checked]

### Auto-Fixed
- [file:line] Added `aria-label="[value]"` on `<button>` (icon-only [icon-name] button)
- [file:line] Added `data-testid="[value]"` on `<div class="[class]">` (structural container)

### Needs Manual Review
- [file:line] Icon-only button with `[icon-name]`: context ambiguous, suggest `aria-label="[suggestion]"`
- [file:line] Button in `@for` loop: suggest `[attr.aria-label]="'[action] ' + item.name"`

### Already Compliant
- [count] elements already have an accessible name
- [count] containers already have `data-testid`
```
