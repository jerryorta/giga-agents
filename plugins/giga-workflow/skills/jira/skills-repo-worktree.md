# 5s: Skills-repo worktree — detail

Skills-repo files are edited in a story worktree, never in `<skillsRepo.path>` or in the checkout that
holds `<skillsRepo.branch>`: that branch is live, and every repo that loads the skills runs it. ⚡ Create
it once, before 5a, in one `Bash` call — it takes this repo's branch name, and a rerun reuses it:

```bash
wt=<skillsRepo.path>-<key-lower> b=$(git branch --show-current)
[ -d "$wt" ] || git -C <skillsRepo.path> worktree add "$wt" -b "$b" <skillsRepo.branch> \
  || git -C <skillsRepo.path> worktree add "$wt" "$b"
git -C "$wt" status --short --branch
```

Each 5a agent that owns a skills-repo file gets the worktree path with its slice and edits there. Its 5r
snapshot is kept apart, `git -C <worktree> diff -- <refactor files> > <scratchpad>/refactor-skills-<slice>.patch`;
the orchestrator concatenates those into `<scratchpad>/refactor-skills.patch`, checks it with
`git -C <worktree> apply --check --cached`, and lists those files under the skills repo's name in
`## Refactor (in place)`, so the skills repo lands its own refactor commit ahead of the feature.
