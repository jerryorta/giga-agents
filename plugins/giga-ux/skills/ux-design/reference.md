# UX Design — technique reference

The scales and checklists behind `SKILL.md`, beside this file, each with its source.

## Cognitive walkthrough (CW)

Expert, task-based inspection of **learnability** for a first-time user (Wharton, Polson & Lewis). At each step:

1. Will users try to achieve the right result?
2. Will users notice that the correct action is available?
3. Will users associate the correct action with the result they're trying to achieve?
4. After the action is performed, will users see that progress is made toward the goal?

Which question fails names the cause: 1 → the goal is not obvious · 2 → the control is not visible · 3 → wrong label (scent) · 4 → no feedback. CW measures learnability only — pair it with the returning-user pass for efficiency.
Source: https://www.nngroup.com/articles/cognitive-walkthroughs/

## PURE — Pragmatic Usability Rating by Experts

- Fix 1–3 target users and the fundamental tasks (under 10). Map each task's happy path into steps; a step starts when the system shows options and ends when the user acts and expects a significant response.
- Rate each step 1 (easy — low load or a known pattern) · 2 (notable cognitive or physical effort, but completable) · 3 (some users fail or quit).
- Task score = sum of its steps; task colour = its worst step. Do not compare totals across tasks.
- With two raters, reconcile to one decided score per step — never average.
Source: https://www.nngroup.com/articles/pure-method/

## Information scent

Scent is the user's estimate, from a label and its context, of whether a link leads to what they want (Pirolli & Card's information foraging, 1999). The label matters most; jargon, brand terms and vague labels ("More", "Explore", "Learn more") lower it. Users leave a path when its scent drops.

| Score | Label vs the job's words |
| --- | --- |
| 3 | Literal match |
| 2 | Clear synonym |
| 1 | Ambiguous — could plausibly hold it |
| 0 | Unrelated, generic or branded |

Two failure shapes: a wrong sibling out-scents the correct link, and scent that weakens deeper in (the destination heading does not echo the clicked label).
Sources: https://www.nngroup.com/articles/information-scent/ · https://doi.org/10.1037/0033-295X.106.4.643

## Tree testing and first-click testing (simulated)

- Tree test: the hierarchy as text only, tasks with one correct node, measured on success, directness (no backtracking) and first click. Task wording must not contain the target's label.
- First click predicts success: Bailey & Wolfson report 87% success after a correct first click vs 46% after a wrong one. MeasuringU's live-site replication found the effect far weaker, so treat it as a strong but variable signal.
- Simulating with one model is optimistic — the author and the participant share knowledge. The blind subagent (no repository, labels only) is the mitigation; the result is still expert-review evidence, not measured success.
Sources: https://www.nngroup.com/articles/tree-testing/ · https://measuringu.com/do-click-tests-predict-live-site-clicks/

## Labels, metaphors and the expectation test

- Heuristic 2, *match between the system and the real world*: use the user's words, phrases and concepts, not internal or brand jargon, and follow real-world conventions so information appears in a natural, logical order.
- A navigation metaphor works only when its real-world meaning predicts what is behind it. Test it as a reverse tree test: show the label alone and ask what the user expects to find there. That expectation is the user's mental model; a mismatch with the actual contents is a mental-model gap, fixed either by changing the label to fit the user or by teaching the model in place (a subtitle, a plain companion word).
- Brand and invented terms score 0–1 on information scent for anyone who has not learnt them. They are fine as product names and costly as signposts.
Sources: https://www.nngroup.com/articles/ten-usability-heuristics/ · https://www.nngroup.com/articles/mental-models/ · https://www.nngroup.com/articles/information-scent/

## Severity scale

| Score | Meaning |
| --- | --- |
| 0 | Not a usability problem |
| 1 | Cosmetic — fix if time allows |
| 2 | Minor — low priority |
| 3 | Major — high priority |
| 4 | Catastrophe — fix before release |

Weigh frequency (on a top-task path or an edge case), impact (blocked, detoured or slowed) and persistence (once, or on every visit).
Source: https://www.nngroup.com/articles/how-to-rate-the-severity-of-usability-problems/

## Heuristics most relevant to findability

From Nielsen's ten: **1** visibility of system status · **2** match between system and the real world (user vocabulary) · **3** user control and freedom (Back, cancel, undo) · **4** consistency and standards (one name per concept across the app) · **6** recognition rather than recall · **7** flexibility and efficiency (shortcuts for returning users).
Also common in apps: unlabelled icons, a junk-drawer "More" menu, inconsistent labels.
Sources: https://www.nngroup.com/articles/ten-usability-heuristics/ · https://www.nngroup.com/articles/top-10-application-design-mistakes/

## Wayfinding and navigation

- **Where am I?** An `h1` echoing the clicked label, an `aria-current` nav item, a distinct `document.title`.
- **Where can I go?** Sibling and parent options are visible, not only inside a hamburger.
- **How do I get back?** Every page below a list or tab has a visible in-app Back or Close on every shell, and it goes where the user expects, restoring the tab and filter they left. Browser Back walks the route history as it stands and is not reviewed: it can revisit a screen an in-app Back replaced, and that is never a finding. It never replaces the in-app control, because an installed app has no browser chrome. Pressed again and again, the in-app Back climbs strictly up the page hierarchy and never revisits a screen; an editor's exit pops history rather than pushing the viewer onto it. A modal closes on Escape and returns focus.
- **Deep link:** the URL opened in a fresh tab renders the same screen, or redirects cleanly through sign-in and back.
- **Hubs:** a dashboard is a navigation hub — it should link directly to each top task.
- **Breadcrumbs** show hierarchy, not history; they end with the current page, unlinked; skip them on shallow or linear apps.
Source: https://www.nngroup.com/articles/breadcrumbs/

## Progressive disclosure, empty states, novice vs expert

- Show frequent options first and the rest on request. Never more than two levels of disclosure, and never hide something a top task needs behind overflow.
- An empty state does three jobs: it says what the system's status is (loading, failed or truly empty), it teaches what belongs here, and it offers the action that fills it.
- Novices need an obvious entry point; experts need speed — recent items, search, keyboard, last-opened. Hide expert shortcuts from novices without removing them.
Sources: https://www.nngroup.com/articles/progressive-disclosure/ · https://www.nngroup.com/articles/empty-state-interface-design/ · https://www.nngroup.com/articles/novice-vs-expert-users/

## Interaction cost

- **The three-click rule is a myth.** No data supports it; clicks differ in cost, and confusion costs more than distance. Judge scent, wayfinding and prominence instead.
- **Hick's law:** decision time grows with the number of equal-weight choices — chunk them and highlight the likely one, without vague umbrella labels.
- **Fitts's law:** small, distant targets are slow; measure touch targets with `getBoundingClientRect` at the real breakpoint (44 px is the common floor).
- **KLM** (Card, Moran & Newell) estimates *expert, error-free* time: about 0.2 s per keystroke, 1.1 s per point, 1.35 s per mental decision. Use it to compare two returning-user paths, never as a novice estimate.
Sources: https://www.nngroup.com/articles/3-click-rule/ · https://lawsofux.com/hicks-law/

## Words — microcopy and brand voice

Every word a user reads or hears is interface. The list below covers common kinds; anything else the user reads follows the same rules.

- **Controls and CTAs:** a verb plus its object, naming the result ("Save note", "Send invite"), never "OK", "Submit" or "Click here". One verb per act across the app, and the confirmation echoes it ("Note saved").
- **Links:** the link text alone predicts the destination, starts with the keyword, and matches the destination's heading. "Learn more" alone carries no scent.
- **Tooltips:** extra help only, never the only place something the task needs is said, and never the only label of an icon (phones have no hover). Short, one idea.
- **Titles and headings:** `document.title` and the `h1` name this page specifically; the heading echoes the label that led there.
- **Help, descriptions and onboarding:** what the user gets, in their words, front-loaded; one idea per sentence.
- **Errors and validation:** next to the problem, say what happened in plain words and how to fix it, keep the user's input, and never blame or show a bare code.
- **Destructive confirmations:** name the object and the consequence; the button repeats the verb ("Delete course"), not "Yes".
- **Notifications and email:** say what changed and for whom; one action.
- **Accessible names:** an icon-only control has one, and a visible label appears inside the control's accessible name (WCAG 2.5.3, *Label in Name*).
- **Rendered, not drafted:** check truncation and wrapping at phone width, text over images, and every state, in the running app.

**Voice versus tone.** A brand's voice stays fixed; its tone shifts with the moment (an error is calmer than a welcome). The voice guide places the brand on the four tone dimensions (funny ↔ serious, formal ↔ casual, respectful ↔ irreverent, enthusiastic ↔ matter-of-fact) and gives do / don't pairs. A brand word fails as a signpost (see Labels above) even when it fits the voice.
**Which voice guide.** The repo lists its guides in `.claude/giga/config.json` under `ux.brandVoice.guides`: each brand with the apps it covers, its guide file, its `status` and any `note`. Pick the guide by the app being worked on, not by the brand's name alone.

- **Owner decisions** in a guide govern new copy. An existing string that breaks one is an `existing` finding with the decided wording as the recommendation; the copy pass to bring screens in line is the owner's to schedule.
- **A draft guide applies**, and each of its open Decisions for the owner is treated as undecided: flag copy that conflicts with the draft's choice without rewriting it.
- **An audience point the guide marks as a guess** is never stated as fact.
- **No guide for the app:** say so and apply the rules above alone.

Sources: https://www.nngroup.com/articles/error-message-guidelines/ · https://www.nngroup.com/articles/tooltip-guidelines/ · https://www.nngroup.com/articles/writing-links/ · https://www.nngroup.com/articles/tone-of-voice-dimensions/ · https://www.w3.org/WAI/WCAG22/Understanding/label-in-name

## Mental models

Designers overestimate how easy their product is to understand. Repeated wrong turns signal a mismatch: either change the system to fit the user's model, or teach the model with labels and in-place help. A simulated card sort only generates hypotheses for regrouping; it is not evidence.
Source: https://www.nngroup.com/articles/mental-models/
