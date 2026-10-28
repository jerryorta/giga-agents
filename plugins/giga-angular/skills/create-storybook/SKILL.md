---
name: create-storybook
description: Generate Storybook story files for an Angular component. Creates the 4-file story set (stories.ts, wrapper component .ts/.html/.scss) with Storybook controls, wrapped in the repo's own storybook review container (theme switching, review status, source link) when it has one. Use when creating stories for new or existing components, or when the user says "add a story", "create storybook", or "write stories for".
---

# Create Storybook Story Files

Generate a complete Storybook story set for an Angular component. Every story renders the component through a wrapper component. When the repo has a review container, the wrapper places the component inside it (`<Prefix>StorybookReviewContainerComponent`), which provides theme switching, review status badges, and GitHub source links; otherwise the wrapper renders the component directly.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `angular`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `prefix` | the repo's component and selector prefix, which names the review container: kebab `<prefix>-storybook-review-container` for the selector, Pascal `<Prefix>StorybookReviewContainerComponent` for the class (each hyphen-separated part capitalised: `acme` → `AcmeStorybookReviewContainerComponent`) | no review container: use the plain wrapper variants below |
| `storybook.reviewContainerImport` | the module that exports the review container and `REVIEW_STATUS` | no review container: use the plain wrapper variants below |
| `storybook.storyExamples` | `{ name, path }` story sets to copy the shape from | Glob `**/*.stories.ts` and read the story nearest the target component |

The review container needs both `prefix` and `storybook.reviewContainerImport`; with either missing, the wrapper renders the component directly, with no review status and no `storybookFilePath`.

## When to Use

- Creating stories for a new component
- Adding story coverage to an existing component that lacks stories
- The user says "add a story", "create storybook", "write stories for [component]"

## Phase 1: Identify the Target Component

Parse `$ARGUMENTS` to determine:
1. **Component path** — if a full path is given, use it directly
2. **Component name** — if only a name is given, search for it:
   ```
   Glob pattern: "**/<component-name>/<component-name>.component.ts"
   ```

Read the component's `.ts`, `.html`, and `.scss` files to understand:
- The selector (e.g., `acme-input-code`)
- Signal inputs (`input()`, `input.required()`)
- Legacy inputs (`@Input()`)
- Outputs (`output()`)
- Imports (which other components it uses)
- Any required providers (Store, services, etc.)

## Phase 2: Determine the Story Directory

Stories live in a `stories/` subdirectory alongside (or near) the component:

```
libs/<domain>/<lib>/src/lib/components/<feature>/
├── <component>/
│   ├── <component>.component.ts
│   ├── <component>.component.html
│   └── <component>.component.scss
└── stories/
    └── <story-name>/
        ├── <story-name>.stories.ts
        ├── <story-name>-stories.component.ts
        ├── <story-name>-stories.component.html
        └── <story-name>-stories.component.scss
```

Look for an existing `stories/` directory near the component. If none exists, create one.

The `<story-name>` is typically the component name without the prefix (e.g., `acme-input-code` → `input-code`).

## Phase 3: Generate the 4 Files

In the templates below, `<Prefix>` and `<prefix>` come from `prefix` and `<storybook.reviewContainerImport>` is that field's value — write the resolved names, never the placeholders.

### File 1: Wrapper Component TypeScript (`<story-name>-stories.component.ts`)

With a review container:

```typescript
import { Component, ViewEncapsulation } from '@angular/core';
import {
  <Prefix>StorybookReviewContainerComponent,
  REVIEW_STATUS,
} from '<storybook.reviewContainerImport>';
// Import the component under review
import { TargetComponent } from '../../path-to-component';

@Component({
  encapsulation: ViewEncapsulation.None,
  host: {
    class: '<story-name>-stories',
  },
  imports: [
    <Prefix>StorybookReviewContainerComponent,
    TargetComponent,
    // Any other component the template uses
  ],
  selector: '<story-name>-stories',
  standalone: true,
  styleUrl: './<story-name>-stories.component.scss',
  templateUrl: './<story-name>-stories.component.html',
})
export class <StoryName>StoriesComponent {
  // Path used for GitHub source link in the footer
  storybookFilePath = 'libs/<domain>/<lib>/src/lib/components/<feature>/stories/<story-name>';

  // Review status badge — use DRAFT for new stories
  reviewStatus = REVIEW_STATUS.DRAFT;

  // Component state — use signals for internal state
  // Map the target component's inputs to controls here
}
```

Without one:

```typescript
import { Component, ViewEncapsulation } from '@angular/core';
// Import the component under review
import { TargetComponent } from '../../path-to-component';

@Component({
  encapsulation: ViewEncapsulation.None,
  host: {
    class: '<story-name>-stories',
  },
  imports: [
    TargetComponent,
    // Any other component the template uses
  ],
  selector: '<story-name>-stories',
  standalone: true,
  styleUrl: './<story-name>-stories.component.scss',
  templateUrl: './<story-name>-stories.component.html',
})
export class <StoryName>StoriesComponent {
  // Component state — use signals for internal state
  // Map the target component's inputs to controls here
}
```

**Key rules:**
- `ViewEncapsulation.None` — required for UI design library stories
- `host.class` must match the selector
- `storybookFilePath` (review container only) — relative path from repo root (without leading `/`)
- `reviewStatus` (review container only) — start with `DRAFT` for new stories
- Import the actual component being tested

### File 2: Wrapper Component Template (`<story-name>-stories.component.html`)

With a review container:

```html
<<prefix>-storybook-review-container
  [reviewStatus]="reviewStatus"
  [storybookFilePath]="storybookFilePath"
>
  <!-- Section headings describe each example -->
  <h4>Default</h4>
  <target-component></target-component>

  <!-- Add more sections showing different configurations -->
  <h4>With Options</h4>
  <target-component [someInput]="someValue"></target-component>
</<prefix>-storybook-review-container>
```

Without one:

```html
<div class="flex flex-col gap-4">
  <h4>Default</h4>
  <target-component></target-component>

  <h4>With Options</h4>
  <target-component [someInput]="someValue"></target-component>
</div>
```

**Template guidelines:**
- With a review container, always wrap in `<<prefix>-storybook-review-container>` and pass `[reviewStatus]` and `[storybookFilePath]`
- Use `<h4>` tags to label different examples/sections
- Show multiple configurations of the component (default, with options, disabled, error state, etc.)
- Use Tailwind for layout (`flex`, `gap`, `grid`) where the repo has it; otherwise lay out in the SCSS file
- For signal values, invoke the getter: `{{ mySig() }}`

### File 3: Wrapper Component Styles (`<story-name>-stories.component.scss`)

```scss
.<story-name>-stories {
  // Add minimal styles for story layout
  // Most styling should use Tailwind in the template
}
```

Keep this minimal — use Tailwind in the template for layout where the repo has it. Only add SCSS for things the utilities can't handle.

### File 4: Stories Configuration (`<story-name>.stories.ts`)

```typescript
import { provideHttpClient } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { applicationConfig, type Meta, type StoryObj } from '@storybook/angular';

import { <StoryName>StoriesComponent } from './<story-name>-stories.component';

const meta: Meta<<StoryName>StoriesComponent> = {
  component: <StoryName>StoriesComponent,
  title: '<Story Title>',
  decorators: [
    applicationConfig({
      providers: [
        provideHttpClient(),
        provideAnimationsAsync(),
        // Add NgRx store, services, etc. if the component needs them
      ],
    }),
  ],
  argTypes: {
    // One entry per wrapper property, typed by the control table below
  },
};

export default meta;
type Story = StoryObj<<StoryName>StoriesComponent>;

export const Default: Story = {
  args: {
    // Default values for controls
  },
};
```

**Stories file rules:**
- `title` controls Storybook sidebar navigation — use a short descriptive name
- `decorators` with `applicationConfig()` provides Angular DI context
- Always include `provideHttpClient()` and `provideAnimationsAsync()`
- Add `provideStore()` if the component uses NgRx
- `argTypes` maps wrapper component properties to Storybook controls
- Export at least one story (`Default`)

### Storybook Control Types

| Input type | argType control |
|-----------|----------------|
| `boolean` | `{ control: { type: 'boolean' } }` |
| `string` | `{ control: { type: 'text' } }` |
| `number` | `{ control: { type: 'number' } }` |
| `enum/union` | `{ control: { type: 'select' }, options: [...] }` |
| `color` | `{ control: { type: 'color' } }` |

## Phase 4: Verify

1. **Check Storybook config** — Glob `**/.storybook/main.ts` (outside `node_modules`) to find the Storybook host, then ensure the library's stories are included in:
   - that `main.ts` (its `stories` globs — story discovery)
   - the `tsconfig.json` beside it (TypeScript compilation)

   With several hosts, use the one whose globs already cover the component's sibling libraries, and add the library the way those siblings are added.

2. **Build check** — If Storybook is running, the new story should appear automatically via HMR.

## Reference: Existing Story Patterns

When unsure about conventions, read an existing story set as a reference: the `storybook.storyExamples` entry whose `name` matches the component's kind (an input, a button, a chart…), or the first entry. With none configured, Glob `**/*.stories.ts` and read the story nearest the target component.
