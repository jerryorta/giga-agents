---
name: verify-theming
description: >-
  Verify and AUTO-FIX theming for an Angular file or component: hardcoded colors, inline color styles and unused or undefined CSS classes become the library's own design tokens, signal calls in templates become `@let` variables, and a banned token namespace is flagged. The token contract, the banned namespaces and any path-scoped variant skill all come from the repo's config. Ends by handing the same file to `/giga-angular:verify-accessibility`. Use when the user says "verify theming", "check the theme tokens", "replace the hardcoded colors", or names a component to theme-check. Args: the file path ($ARGUMENTS).
---

# Verify and AUTO-FIX theming

Verify and AUTO-FIX theming for the file: $ARGUMENTS

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `angular`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `prefix` | the component and token prefix, only when the target library's `project.json` has none | ask the user for the prefix |
| `theming.tokenFile` | the token contract of the file's domain: a path pattern with `<domain>` and `<prefix>` placeholders | look for a themes library beside the file's library and read its token file; none found, ask the user which token file governs the file |
| `theming.tokenDocs` | the rulebook that explains the token contract, same placeholders | read the `AGENTS.md` beside the token file, if there is one |
| `theming.standards` | the styling standards, as paths or `path § heading` entries; they win over this skill's text | the rules below are the standard |
| `theming.bannedTokens` | token namespaces the repo's standards ban (for example `--legacy-`); each hit is flagged | nothing is flagged on namespace |
| `theming.variants` | `[{ "paths": [...], "skill": "<name>" }]`: path prefixes that another skill owns | every file is handled here |
| `workflow.notify` (read from `workflow`, not `angular`) | the command that queues a desktop notification | send no notification |

The prefix is read from the target library's `project.json` `prefix`; `prefix` in config is only the fallback.

## Variant routing

Before anything else, test the target against each `theming.variants[].paths`. When a path prefix covers the file, stop and hand the file to that entry's `skill`, with the same arguments. The rest of this skill is for every other file.

## Phase 1: Analysis

1. Read the file specified.
2. If the file is an HTML template (`*.html`), also read the associated:
   - TypeScript component file: check the `host` property classes and any inline `template` with color classes
   - SCSS file: check for hardcoded color values
3. Read every doc in `theming.standards`.
4. Read the token contract of the file's domain. Fill `<domain>` from the path (`libs/<domain>/...`) and `<prefix>` from the target library's `project.json`, expand `theming.tokenFile` and `theming.tokenDocs`, and read both. For a shared library with no themes library of its own, read the token file that library ships beside its components.
5. Analyze all related files for:
   - Hardcoded utility-framework colors (for example `text-gray-500`, `bg-blue-600`, `border-red-400`)
   - Inline color styles (`style="color: #fff"`, `[style.color]="'red'"`)
   - CSS color values that should use theme tokens (`color: #333`, `background: rgba(0,0,0,0.5)`)
   - Host classes in the component decorator that contain color classes
   - Inline templates in the decorator with color classes
   - `console.log` statements that should be removed
6. Identify SCSS that the styling standards say belongs in utility classes:
   - Colors, typography, layout and sizing declarations with an unambiguous utility equivalent
   - Keep in SCSS: custom property definitions, pseudo-elements and selectors a utility cannot express
   - With no `theming.standards`, skip this step and migrate colors only
7. Verify CSS class usage in both directions:
   - SCSS to HTML: every class defined in SCSS is used in the template
   - HTML to SCSS: every BEM-style class used in HTML is defined
   - Report unused classes (defined but not used) and undefined classes (used but not defined)
8. For each color found:
   - Decide whether it should be replaced with a domain theme token
   - Map the `--<prefix>-*` token, with its literal fallback, by hue, lightness and purpose
   - Flag any token whose name starts with a `theming.bannedTokens` prefix: a token namespace the repo's standards ban has no definition behind it
9. Skip utility theme classes the domain's token docs list.
10. Check for signal calls in the HTML template:
    - A pattern like `signalName()` called directly in the template
    - Signals are declared once at the top with `@let _signalName = signalName();`, and every reference uses the `@let` variable
    - Report each direct signal call that should use a `@let` variable

## Phase 1b: File structure check

Check the component's file structure before applying theming fixes.

1. If the `.ts` file uses an inline `template:` or `styles:` instead of `templateUrl` and `styleUrl`, split it first:
   - Extract the inline template to `<name>.component.html`
   - Extract the inline styles to `<name>.component.scss`
   - Point the `.ts` file at both with `templateUrl` and `styleUrl`
   - Wrap the SCSS in the component's host class (for example `.<prefix>-name { ... }`) when the library's standards require it
2. This applies to every component, library or application.
3. The library's own rulebook (the `AGENTS.md` nearest the file) names the required file shape; follow it where it differs.

## Phase 2: Auto-Fix (safe changes)

After analysis, apply these fixes without asking.

### Always auto-fix

- **Hardcoded utility colors**: replace with the domain token equivalent and its literal fallback, for example `text-gray-500` becomes `text-[var(--<prefix>-on-surface-variant,#…)]`
- **Signal `@let` declarations**: add `@let` at the top of the template and replace each `signalName()` call with `_signalName`
- **`console.log` removal**: delete `console.log`, `console.warn` and `console.error` statements
- **Inline color styles**: replace with theme-token utility classes
- **Unused CSS classes**: remove from SCSS
- **Undefined CSS classes**: remove from HTML
- **Simple SCSS to utility migrations** where the mapping is unambiguous and `theming.standards` allows it:
  - `font-weight: 600` becomes `font-semibold`
  - `display: flex; flex-direction: column` becomes `flex flex-col`
  - `gap: 8px` becomes `gap-2`
  - `padding: 16px` becomes `p-4`
  - Color properties using `var(--<prefix>-*)` become the corresponding token utility

### Do NOT auto-fix (report only)

- Ambiguous color token mappings (several tokens fit)
- Complex layout refactors where the utility equivalent is unclear
- Custom property definitions
- Pseudo-elements

## Phase 3: Report

After applying fixes, output this summary.

```
## Theming Verification: [filename]

### Files Analyzed
- [every file checked]

### Auto-Fixed
- [file:line] `[before]` -> `[after]` (reason)

### Needs Manual Review
- [file:line] `[current]` -> `[suggested]` (why it was not auto-fixed)

### Correctly Themed (no changes needed)
- [items already using proper theme tokens]

### Exceptions
- [utility classes or intentional custom colors]
```

## Phase 4: Accessibility check

After the theming report, run `/giga-angular:verify-accessibility` on the same file to check for missing accessible names and test ids.

## Phase 5: Notification

When `workflow.notify` is set in the config, queue one line through that command: `verify-theming complete for [filename]: [N] auto-fixed, [M] need manual review.` With `workflow.notify` unset, send nothing.
