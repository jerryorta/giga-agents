# Merge modes — detail (`epic-branch` and `direct`)

## Branch model

- **`"epic-branch"`:** every story is implemented in the main checkout **directly on the shared `config.epicBranch`** and committed there. `/giga-workflow:epic-story-complete` pushes the epic branch and transitions the ticket to Done (no per-story PR). The whole epic lands on `<git.mainBranch>` via **one PR at the end**. Requires `config.epicBranch`.
- **`"direct"`:** every story gets the same per-story `<git.branchPrefix><key>-<slug>` branch as PR mode, cut from `origin/<git.mainBranch>`, and no PR. `/giga-workflow:epic-story-complete` commits on it, fast-forwards `<git.mainBranch>` to it, pushes `<git.mainBranch>`, transitions the ticket to Done and chains `/giga-workflow:post-merge-cleanup`. Each story lands on `<git.mainBranch>` on its own, for repos that deploy on every push to it.

## 9a — Epic-branch mode

**Epic-branch mode (`config.mergeMode === "epic-branch"`)** — work in the main checkout directly on `config.epicBranch`; the story is committed onto it (no per-story branch, no worktree). Ensure the epic branch exists and is current:

⚡ One `Bash` call:

```
git fetch origin
# First story of the epic? Create the epic branch from origin/<git.mainBranch>:
#   git checkout -b <config.epicBranch> origin/<git.mainBranch> && git push -u origin <config.epicBranch>
# Otherwise check out the existing epic branch and fast-forward it:
git checkout <config.epicBranch> && git pull --ff-only && git status --porcelain && git rev-parse --short HEAD
```

The `--porcelain` output in the same call answers the uncommitted-changes question below without a
second round trip.

Every later step (the `/giga-workflow:jira` hand-off, build/test, `/giga-workflow:epic-story-complete`) runs in the main checkout on `config.epicBranch`. Report: `On epic branch <config.epicBranch> at <short-sha>`.

**If the epic branch has uncommitted changes** (e.g. a prior story left work mid-flight) → surface them and ask the user whether to continue on top or stash first; do not discard in-progress work.

## 9c — Hand-off outcomes

- **Epic-branch mode:** commit onto `config.epicBranch`, push it (`git push origin <config.epicBranch>`), and transition the ticket to **Done** (no per-story PR — the epic lands on `<git.mainBranch>` via one PR at the end).
- **Direct mode:** commit on the story branch, rebase it onto `origin/<git.mainBranch>` if that moved, fast-forward `<git.mainBranch>` to it and push `<git.mainBranch>` (no PR; the story branch is never pushed), transition the ticket to **Done**, and chain `/giga-workflow:post-merge-cleanup`, which deletes the local branch and moves the story out of its wave.
- **Skill-only story** (any mode; the whole diff is in the skills repo's story worktree): land it on the skills repo's live branch and push it, then take the ticket to **Done** with no PR.
- **Mixed story** (skills-repo files too): the skills leg lands on the skills repo's live branch and is pushed first, so it is live before this repo's PR is reviewed.
