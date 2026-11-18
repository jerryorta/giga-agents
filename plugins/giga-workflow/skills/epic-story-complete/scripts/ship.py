#!/usr/bin/env python3
"""Ship a finished epic story once the session's confirmation gate has passed.

  ship.py preflight <board> <KEY> [--secrets]   print the facts the gate shows; change nothing
  ship.py run <handoff.json>                    commit, push, PR, Jira, merge, plan files, cleanup

Every stage checks its own state before acting, so re-running after a stop resumes where the last
run stopped. Jira goes through the plans script (`transition`, `comment`, `board`), never an MCP.
The handoff format and the session's half: the SKILL.md beside this folder.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

REVIEW = ["In Review", "Code Review", "Ready for Review"]
DONE = ["Done"]
PROCEED = {"CLEAN", "UNSTABLE", "HAS_HOOKS"}
ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s")
HERE = Path(__file__).resolve().parent
POLL = float(os.environ.get("SHIP_POLL_SECONDS", "4"))


class Stop(Exception):
    def __init__(self, stage, reason, state):
        super().__init__(reason)
        self.stage, self.reason, self.state = stage, reason, state


def sh(cmd, cwd=None, inp=None, shell=False):
    p = subprocess.run(cmd, cwd=cwd, input=inp, text=True, capture_output=True, shell=shell)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def git(*args, cwd=None):
    return sh(["git", *args], cwd=cwd)


def tail(text, n=15):
    return "\n".join(text.strip().splitlines()[-n:])


def expand(p, base=None):
    if not p:
        return None
    p = os.path.expanduser(p)
    if base and not os.path.isabs(p):
        p = os.path.join(base, p)
    return os.path.normpath(p)


def token(key):
    return re.compile(rf"(?<![A-Za-z0-9-]){re.escape(key)}(?![0-9])")


class Ctx:
    def __init__(self, board, key):
        rc, root, _ = git("rev-parse", "--show-toplevel")
        if rc:
            raise Stop("preflight", "not inside a git repo", "nothing done")
        self.root = root
        giga = Path(root, ".claude", "giga")
        cfg_file = giga / "config.json"
        wf = (json.loads(cfg_file.read_text()) if cfg_file.exists() else {}).get("workflow", {})
        board_file = giga / f"epic.{board}.json"
        if not board_file.exists():
            boards = ", ".join(sorted(p.name for p in giga.glob("epic.*.json"))) or "none"
            raise Stop("preflight", f"no {board_file.name} (boards: {boards})", "nothing done")
        b = json.loads(board_file.read_text())
        self.board, self.key = board, key.upper()
        self.krx = f"{self.key}([^0-9]|$)"
        g = wf.get("git", {})
        self.main = g.get("mainBranch", "main")
        self.prefix = g.get("branchPrefix", "feat/")
        self.method = g.get("mergeMethod", "squash")
        pl = wf.get("plans", {})
        self.plans_repo, self.plans_script = expand(pl.get("repo")), expand(pl.get("script"))
        self.auto_push = bool(pl.get("autoPush"))
        sk = wf.get("skillsRepo") or {}
        self.sk_path = expand(sk.get("path"))
        self.sk_branch = sk.get("branch", "main")
        self.sk_push = sk.get("push") or f"git push origin {self.sk_branch}"
        self.sk_name = os.path.basename(self.sk_path) if self.sk_path else None
        sec = wf.get("secrets", {})
        self.shared_secret_repo = expand(sec.get("sharedRepo"))
        self.require_private = sec.get("requirePrivate", True) is not False
        self.notify = wf.get("notify")
        self.mode = b.get("mergeMode") or "pr"
        self.epic = b.get("epicKey")
        self.epic_branch = b.get("epicBranch")
        self.domain_secret_repo = expand(b.get("secretsRepo"), root)
        self.jql = b.get("jql")
        self.ordering = b.get("storyOrdering")
        self.group = b.get("groupLabel") or "Wave"
        self.done_msg = b.get("completionMessage") or "no story is To Do"
        self.build_cmd = b.get("buildCommand")
        self.branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=root)[1]

    def plans(self, *args, inp=None):
        if not self.plans_script:
            raise RuntimeError("no plans.script in .claude/giga/config.json")
        rc, out, err = sh(["python3", self.plans_script, *args], inp=inp)
        if rc:
            raise RuntimeError((err or out or f"plans {args[0]} exited {rc}").splitlines()[-1])
        return out

    def ticket(self):
        rows = json.loads(self.plans("board", "--jql", f"key = {self.key} OR parent = {self.key}") or "[]")
        story = next((r for r in rows if r.get("key") == self.key), None)
        return story, [r for r in rows if r.get("key") != self.key]

    def ahead_commits(self):
        rc, out, _ = git("log", "--format=%h %s", "-E", f"--grep={self.krx}", f"origin/{self.main}..HEAD", cwd=self.root)
        return out.splitlines() if rc == 0 and out else []

    def open_pr(self):
        rc, out, _ = sh(["gh", "pr", "list", "--head", self.branch, "--state", "all",
                         "--json", "number,url,state", "--limit", "5"], cwd=self.root)
        rows = json.loads(out) if rc == 0 and out else []
        return next((r for r in rows if r["state"] in ("OPEN", "MERGED")), None)

    def skills(self):
        if not self.sk_path or self.branch in (self.main, "master", self.sk_branch, "HEAD"):
            return None
        sp, sb, b = self.sk_path, self.sk_branch, self.branch
        wt = git("-C", sp, "for-each-ref", "--format=%(worktreepath)", f"refs/heads/{b}")[1]
        git("-C", sp, "fetch", "-q", "origin", sb)
        base = next((r for r in (f"origin/{sb}", "origin/HEAD")
                     if git("-C", sp, "rev-parse", "-q", "--verify", r)[0] == 0), None)
        rc, ahead, _ = git("-C", sp, "log", "--oneline", f"{sb}..{b}")
        ahead = ahead if rc == 0 else ""
        unpushed = git("-C", sp, "log", "--oneline", "--branches", "-E", f"--grep={self.krx}",
                       *([f"^{base}"] if base else []))[1]
        riding = (git("-C", sp, "log", "--oneline", "-E", f"--grep={self.krx}", "--invert-grep", f"{base}..{sb}")[1]
                  if base else "the whole branch (no remote base)")
        landed = git("-C", sp, "log", "-1", "--format=%h", "-E", f"--grep={self.krx}", sb)[1]
        dirty = git("-C", wt, "status", "--short")[1] if wt else ""
        return {"worktree": wt, "dirty": dirty, "ahead": ahead, "unpushed": unpushed, "riding": riding,
                "landed": landed, "pending": bool(wt or ahead or unpushed)}

    def secret_repos(self):
        return [r for r in (self.domain_secret_repo, self.shared_secret_repo) if r]


# ---------------------------------------------------------------- preflight

def preflight(board, key, read_secret_repos):
    c = Ctx(board, key)
    out, refuse = [], []
    out.append(f"Board:       {c.board} · {c.mode} · epic {c.epic}")
    expected = c.epic_branch if c.mode == "epic-branch" else f"{c.prefix}{c.key.lower()}-…"
    on_branch = (c.branch == c.epic_branch) if c.mode == "epic-branch" else \
        c.branch.lower().startswith(f"{c.prefix}{c.key.lower()}-")
    out.append(f"Branch:      {c.branch} {'✓' if on_branch else '✗ expected ' + str(expected)}")
    if c.branch in (c.main, "master"):
        refuse.append(f"on {c.branch} — this skill never runs on the base branch")
    elif not on_branch:
        refuse.append(f"branch {c.branch} does not match {expected}")
    try:
        story, subs = c.ticket()
        if story:
            flag = "" if story.get("status") == "In Progress" else "   ⚠ not In Progress"
            out.append(f"Ticket:      {c.key} · {story.get('status')} · {story.get('type')} — {story.get('summary')}{flag}")
        else:
            out.append(f"Ticket:      {c.key} not found by the plans script")
        out.append("Sub-tasks:   " + (", ".join(f"{s['key']} {s['status']}" for s in subs) or "none"))
    except RuntimeError as e:
        out.append(f"Ticket:      unreadable — {e}")
    if c.mode == "pr":
        pr = c.open_pr()
        out.append("PR:          " + (f"#{pr['number']} {pr['state']} — {pr['url']}" if pr else "none"))
        if pr:
            refuse.append(f"PR #{pr['number']} is already {pr['state'].lower()} — "
                          f"use /giga-workflow:epic-merge-pr {pr['number']}")
    status = git("status", "--short", cwd=c.root)[1]
    adds = dels = 0
    for line in git("diff", "HEAD", "--numstat", cwd=c.root)[1].splitlines():
        a, d, _ = (line.split("\t") + ["", "", ""])[:3]
        adds += int(a) if a.isdigit() else 0
        dels += int(d) if d.isdigit() else 0
    files = status.splitlines()
    out.append(f"Files:       {len(files)} changed (+{adds} / -{dels} tracked)")
    out += [f"  {f}" for f in files]
    ahead = c.ahead_commits()
    out.append("KEY commits: " + ("; ".join(ahead) if ahead else "none"))
    sk = c.skills()
    if sk is None:
        out.append("Skills leg:  not configured")
    else:
        shape = "pending" if sk["pending"] else "not pending"
        out.append(f"Skills leg:  {shape} — worktree {sk['worktree'] or 'none'}"
                   + (f" · landed {sk['landed']}" if sk["landed"] else ""))
        for label, val in (("files", sk["dirty"]), ("on branch", sk["ahead"]),
                           ("unpushed", sk["unpushed"]), ("riding along", sk["riding"] if sk["pending"] else "")):
            if val:
                out.append(f"  {label}:")
                out += [f"    {v}" for v in val.splitlines()]
    pending = bool(sk and sk["pending"])
    if not files and not pending and not ahead:
        refuse.append("nothing to commit")
    if not files and pending and ahead:
        refuse.append("this repo already has KEY commits made outside this skill and the skills leg is pending — "
                      "the owner decides how they ship")
    if read_secret_repos:
        repos = c.secret_repos()
        if not repos:
            out.append("Secrets:     skipped — no secrets repo configured")
        for r in repos:
            out.append(f"Secrets:     {r} — {secret_state(c, r)}")
    out.append("Refuse:      " + ("; ".join(refuse) if refuse else "none"))
    print("\n".join(out))
    return 1 if refuse else 0


def secret_state(c, repo):
    real = os.path.realpath(repo)
    if not os.path.isdir(os.path.join(real, ".git")) and git("-C", real, "rev-parse")[0]:
        return "skipped — missing"
    git("-C", real, "fetch", "-q")
    br = git("-C", real, "rev-parse", "--abbrev-ref", "HEAD")[1]
    if br != c.main:
        return f"skipped — on {br}, not {c.main}"
    rc, lr, _ = git("-C", real, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    if rc or lr.split() != ["0", "0"]:
        return f"skipped — ahead/behind origin ({lr or 'no upstream'})"
    paths = [line[3:] for line in git("-C", real, "status", "--porcelain")[1].splitlines()]
    return f"{len(paths)} pending: {', '.join(paths)}" if paths else "clean"


# ---------------------------------------------------------------- run

class Ship:
    def __init__(self, handoff):
        self.h = handoff
        self.c = Ctx(handoff["board"], handoff["key"])
        self.until = handoff.get("until", "review") if self.c.mode == "pr" else self.c.mode
        self.trailer = handoff["commit"]["trailer"]
        self.rows, self.warns = [], []
        self.res = {"key": self.c.key, "mode": self.c.mode, "pr": None, "prUrl": None, "sha": None,
                    "mergeSha": None, "skillsSha": None, "ticket": None, "epicClosed": False,
                    "epic": self.c.epic, "next": None, "stopped": None}

    def row(self, label, value):
        self.rows.append(f"{label + ':':<11}{value}")

    def warn(self, text):
        self.warns.append(text)

    def move(self, key, names):
        try:
            return self.c.plans("transition", key, *names)
        except RuntimeError as e:
            self.warn(f"{key} not moved to {names[0]} — {e}")
            return None

    # -- stages

    def build(self):
        if not self.h.get("build") or not self.c.build_cmd:
            return
        rc, out, err = sh(self.c.build_cmd, cwd=self.c.root, shell=True)
        if rc:
            raise Stop("build", tail(out + "\n" + err), "nothing staged — fix the build and re-run")
        self.row("Build", "re-run ✓")

    def land_skills(self, sk):
        c, sc, no_push = self.c, self.h.get("skills") or {}, self.h.get("noPush")
        sp, sb, b, wt = c.sk_path, c.sk_branch, c.branch, sk["worktree"]
        live = git("-C", sp, "for-each-ref", "--format=%(worktreepath)", f"refs/heads/{sb}")[1]

        def has():
            return git("-C", sp, "rev-parse", "-q", "--verify", f"refs/heads/{b}")[0] == 0

        def anc(a, d):
            return git("-C", sp, "merge-base", "--is-ancestor", a, d)[0] == 0

        if wt and git("-C", wt, "status", "--porcelain")[1]:
            if not sc.get("subject"):
                raise Stop("skills commit", "the story worktree has changes but the handoff has no skills subject",
                           "nothing landed")
            patch = sc.get("refactorPatch")
            done = re.search(r"^refactor\(", git("-C", wt, "log", "--format=%s", f"{sb}..HEAD")[1], re.M)
            if patch and not done:
                if git("-C", wt, "apply", "--cached", patch)[0] or \
                        sh(["git", "-C", wt, "commit", "-q", "-m", sc["refactorSubject"], "-m", self.trailer])[0]:
                    raise Stop("skills refactor commit", f"could not commit {patch}", "nothing landed")
            git("-C", wt, "add", "-A")
            rc, out, err = sh(["git", "-C", wt, "commit", "-q", "-m", sc["subject"], "-m", self.trailer])
            if rc:
                raise Stop("skills commit", tail(out + "\n" + err),
                           "changes stay in the story worktree; nothing landed — fix and re-run, never --no-verify")
        if no_push:
            self.row("Skills", "committed in the story worktree (--no-push)")
            return None
        if has() and not anc(b, sb):
            if not anc(sb, b):
                if not wt:
                    raise Stop("skills rebase", f"{sb} moved and there is no story worktree to rebase in",
                               "commit safe on the story branch")
                if git("-C", wt, "rebase", "-q", sb)[0]:
                    git("-C", wt, "rebase", "--abort")
                    raise Stop("skills rebase", "rebase conflict — not landed",
                               f"commit safe on the story branch; {sb} and this repo untouched")
            rc = git("-C", live, "merge", "-q", "--ff-only", b)[0] if live else \
                git("-C", sp, "fetch", "-q", ".", f"{b}:{sb}")[0]
            if rc:
                held = git("-C", live or sp, "status", "--short")[1]
                raise Stop("skills fast-forward", f"refused — the checkout holding {sb} has uncommitted edits:\n{held}",
                           "never stash or discard them; once the owner moves them, a re-run lands the story")
        rc, out, err = sh(c.sk_push, cwd=wt or live or sp, shell=True)
        if rc:
            raise Stop("skills push", tail(out + "\n" + err),
                       f"on the local {sb}, not pushed — never force-push; bring origin/{sb} in and re-run")
        sha = git("-C", sp, "log", "-1", "--format=%h", "-E", f"--grep={c.krx}", sb)[1]
        if not sha:
            raise Stop("skills push", f"no {c.key} commit on {sb} after the push", "check the skills repo by hand")
        if wt and git("-C", sp, "worktree", "remove", wt)[0]:
            self.warn(f"story worktree {wt} not removed")
        if has() and anc(b, sb):
            git("-C", sp, "branch", "-D", b)
        self.res["skillsSha"] = sha
        self.row("Skills", f"{sha} on {sb} (pushed ✓) — {c.sk_name}")
        return sha

    def commit(self):
        c, cm = self.c, self.h["commit"]
        status = git("status", "--porcelain", cwd=c.root)[1]
        ahead = c.ahead_commits()
        if not status:
            if ahead:
                sha = ahead[0].split()[0]
                self.row("Commit", f"{sha} — already committed")
                return sha
            return None
        subjects = git("log", "--format=%s", f"origin/{c.main}..HEAD", cwd=c.root)[1]
        patch = cm.get("refactorPatch")
        if patch and not re.search(rf"^refactor\(.*{re.escape(c.key)}", subjects, re.M):
            if not os.path.exists(patch):
                raise Stop("refactor commit", f"snapshot {patch} is missing — rebuild it and re-run", "nothing committed")
            if git("apply", "--cached", patch, cwd=c.root)[0]:
                raise Stop("refactor commit", f"{patch} does not apply to the index", "nothing committed")
            rc, out, err = sh(["git", "commit", "-q", "-m", cm["refactorSubject"], "-m", self.trailer], cwd=c.root)
            if rc:
                raise Stop("refactor commit", tail(out + "\n" + err),
                           "refactor staged, nothing committed — fix and re-run, never --no-verify")
        git("add", "-A", cwd=c.root)
        rc, out, err = sh(["git", "commit", "-q", "-m", cm["subject"], "-m", self.trailer], cwd=c.root)
        if rc:
            raise Stop("commit", tail(out + "\n" + err),
                       "changes staged, nothing committed — fix and re-run, never --no-verify or --amend")
        sha = git("rev-parse", "--short", "HEAD", cwd=c.root)[1]
        self.row("Commit", f"{sha} — {cm['subject']}")
        return sha

    def push_pr(self):
        c = self.c
        rc, _, err = git("push", "-q", "-u", "origin", c.branch, cwd=c.root)
        if rc:
            raise Stop("push", tail(err), "committed locally, not pushed — never force-push")
        pr = c.open_pr()
        if not pr:
            body = self.h.get("prBody")
            if not body:
                raise Stop("pr", "the handoff has no prBody", "committed and pushed; re-run with a PR body")
            rc, out, err = sh(["gh", "pr", "create", "--title", self.h["commit"]["subject"], "--base", c.main,
                               "--head", c.branch, "--body-file", "-"], cwd=c.root, inp=body)
            if rc:
                raise Stop("pr", tail(err or out), "committed and pushed; open the PR by hand or re-run")
            url = out.splitlines()[-1].strip()
            pr = {"number": int(url.rstrip("/").rsplit("/", 1)[1]), "url": url, "state": "OPEN"}
        self.res.update(pr=pr["number"], prUrl=pr["url"])
        return pr

    def merge(self, pr):
        c, n = self.c, str(pr["number"])
        state = f"committed, pushed, PR #{n} open, ticket In Review — resume with /giga-workflow:epic-merge-pr {n}"
        updated = False
        for _ in range(30):
            rc, out, err = sh(["gh", "pr", "view", n, "--json", "state,mergeStateStatus"], cwd=c.root)
            if rc:
                raise Stop("merge", tail(err), state)
            d = json.loads(out)
            if d["state"] == "MERGED":
                break
            if d["state"] == "CLOSED":
                raise Stop("merge", "the PR is closed", state)
            s = d.get("mergeStateStatus")
            if s in PROCEED:
                rc, out, err = sh(["gh", "pr", "merge", n, f"--{c.method}", "--delete-branch"], cwd=c.root)
                if rc:
                    raise Stop("merge", tail(err or out), state)
                break
            if s == "BEHIND" and not updated:
                sh(["gh", "pr", "update-branch", n], cwd=c.root)
                updated = True
            elif s not in ("UNKNOWN", "BEHIND", None):
                raise Stop("merge", f"mergeStateStatus={s} — not merged", state + " — do not run cleanup")
            time.sleep(POLL)
        else:
            raise Stop("merge", "GitHub never reported a mergeable state", state)
        rc, out, _ = sh(["gh", "pr", "view", n, "--json", "state,mergedAt,mergeCommit"], cwd=c.root)
        d = json.loads(out) if rc == 0 else {}
        if d.get("state") != "MERGED" or not d.get("mergedAt"):
            raise Stop("verify", f"PR #{n} reads {d.get('state')} after the merge", state)
        msha = (d.get("mergeCommit") or {}).get("oid", "")[:7]
        git("checkout", "-q", c.main, cwd=c.root)
        git("fetch", "-q", "origin", cwd=c.root)
        git("pull", "-q", "--ff-only", cwd=c.root)
        lr = git("rev-list", "--left-right", "--count", f"{c.main}...origin/{c.main}", cwd=c.root)[1].split()
        if lr and lr[0] != "0":
            self.warn(f"local {c.main} has {lr[0]} commit(s) origin/{c.main} lacks — check before the next story")
        if git("rev-parse", "-q", "--verify", f"refs/heads/{c.branch}", cwd=c.root)[0] == 0:
            git("branch", "-D", c.branch, cwd=c.root)
        if git("ls-remote", "--heads", "origin", c.branch, cwd=c.root)[1]:
            git("push", "-q", "origin", "--delete", c.branch, cwd=c.root)
        git("remote", "prune", "origin", cwd=c.root)
        self.res["mergeSha"] = msha
        self.row("Merged", f"PR #{n} → {msha} on {c.main} ({c.method}) — {pr['url']}")
        self.row("Branch", f"{c.branch} deleted (local + remote) · local {c.main} synced ✓")
        return msha

    def land_epic_branch(self):
        c = self.c
        if git("push", "-q", "origin", c.epic_branch, cwd=c.root)[0]:
            if git("pull", "-q", "--rebase", "origin", c.epic_branch, cwd=c.root)[0]:
                git("rebase", "--abort", cwd=c.root)
                raise Stop("push", f"{c.epic_branch} moved and the rebase conflicts", "commit safe locally — never force-push")
            rc, _, err = git("push", "-q", "origin", c.epic_branch, cwd=c.root)
            if rc:
                raise Stop("push", tail(err), "commit safe locally — never force-push")
        self.row("Pushed", f"{c.epic_branch} ✓")

    def land_direct(self):
        c, story = self.c, self.c.branch
        for attempt in (1, 2):
            if git("fetch", "-q", "origin", c.main, cwd=c.root)[0]:
                raise Stop("fetch", f"could not fetch origin/{c.main}", "commit safe on the story branch")
            if git("merge-base", "--is-ancestor", f"origin/{c.main}", "HEAD", cwd=c.root)[0]:
                if git("rebase", "-q", f"origin/{c.main}", cwd=c.root)[0]:
                    git("rebase", "--abort", cwd=c.root)
                    raise Stop("rebase", "rebase conflict — not merged",
                               f"commit safe on the story branch; {c.main} untouched")
            git("checkout", "-q", c.main, cwd=c.root)
            if git("merge", "-q", "--ff-only", story, cwd=c.root)[0]:
                extra = git("log", "--oneline", f"origin/{c.main}..{c.main}", cwd=c.root)[1]
                git("checkout", "-q", story, cwd=c.root)
                raise Stop("fast-forward", f"local {c.main} carries commits origin lacks:\n{extra}",
                           f"{c.main} unchanged; commit safe on the story branch")
            rc, _, err = git("push", "-q", "origin", c.main, cwd=c.root)
            if not rc:
                break
            git("checkout", "-q", story, cwd=c.root)
            git("branch", "-f", c.main, f"origin/{c.main}", cwd=c.root)
            if "protected" in err.lower() or "rule" in err.lower() or attempt == 2:
                raise Stop("push", tail(err), f"local {c.main} is ahead of origin — push it yourself, "
                           f"or switch the board to \"pr\" with /giga-workflow:epic-config {c.board}; never force-push")
        sha = git("log", "-1", "--format=%h", "-E", f"--grep={c.krx}", c.main, cwd=c.root)[1]
        git("branch", "-D", story, cwd=c.root)
        self.row("Pushed", f"{c.main} ✓ (fast-forward) · {story} deleted (local)")
        return sha

    def comment(self, heading, paragraphs):
        body = f"### {heading}\n\n" + "\n\n".join(p for p in paragraphs if p) + "\n"
        try:
            self.c.plans("comment", self.c.key, inp=body)
            self.row("Comment", "posted ✓")
        except RuntimeError as e:
            self.row("Comment", f"failed — {e}")

    def subtasks(self):
        try:
            rows = json.loads(self.c.plans("board", "--jql",
                                           f"parent = {self.c.key} AND statusCategory != Done") or "[]")
        except RuntimeError as e:
            self.warn(f"sub-tasks unread — {e}")
            return
        moved = [r["key"] for r in rows if self.move(r["key"], DONE)]
        self.row("Sub-tasks", f"{len(moved)} → Done" if rows else "none open")

    def outcome(self, label):
        c, o = self.c, self.h.get("outcome") or {}
        try:
            plan = Path(c.plans("ensure", c.key))
        except RuntimeError as e:
            self.row("Outcome", f"not written — {e}")
            return
        text = plan.read_text()
        m = re.search(r"^## Outcome.*$", text, re.M)
        sk = self.res["skillsSha"]
        if m:
            head = m.group(0)
            if sk and sk not in head:
                new = head[:-1] + f" · {c.sk_name} {sk})" if head.endswith(")") else head + f" · {c.sk_name} {sk}"
                plan.write_text(text.replace(head, new, 1))
            self.row("Outcome", f"{c.board}/{c.key}.md § Outcome already recorded")
            return
        if not o.get("text"):
            self.row("Outcome", "not written — the handoff has no outcome text")
            return
        pins = o.get("pins") or []
        block = f"\n## Outcome — shipped ({label})\n\n{o['text'].strip()}\n"
        if pins:
            block += "\n### Pinned\n\n" + "".join(f"- {p}\n" for p in pins)
        plan.write_text(text.rstrip("\n") + "\n" + block)
        self.row("Outcome", f"{c.board}/{c.key}.md § Outcome ✓ ({len(pins)} pin(s))" if pins else
                 f"{c.board}/{c.key}.md § Outcome ✓ — nothing pinned")

    def story_epic(self):
        try:
            for line in Path(self.c.plans("ensure", self.c.key)).read_text().splitlines():
                if line.startswith("epic:"):
                    return line.split(":", 1)[1].strip() or self.c.epic
        except RuntimeError:
            pass
        return self.c.epic

    def section(self, epic, name):
        try:
            p, s, e = self.c.plans("section", epic, name, "--range").split()[-3:]
            return p, int(s), int(e)
        except (RuntimeError, ValueError):
            return None

    def shipped_line(self, epic, stamp, remove_wave):
        c = self.c
        wave, ship = self.section(epic, "Wave") if remove_wave else None, self.section(epic, "Shipped")
        try:
            path = Path((wave or ship or [c.plans("ensure", epic)])[0])
        except RuntimeError as e:
            self.row("Wave plan", f"not updated — {e}")
            return
        lines = path.read_text().split("\n")
        tok, edits, wave_n, note = token(c.key), [], None, ""
        heading = re.compile(rf"^#{{2,4}}\s.*?\b(?:Wave|{re.escape(c.group)})\s+(\d+)", re.I)
        if wave:
            s, e = wave[1] - 1, min(wave[2], len(lines))
            hits = [i for i in range(s, e) if ITEM.match(lines[i]) and tok.search(lines[i])]
            if len(hits) == 1:
                i = hits[0]
                hj = next((j for j in range(i, s - 1, -1) if heading.match(lines[j])), None)
                wave_n = heading.match(lines[hj]).group(1) if hj is not None else None
                drop = [i]
                if hj is not None and hj > s:
                    nxt = next((j for j in range(hj + 1, e) if lines[j].startswith("#")), e)
                    if all(not lines[j].strip() for j in range(hj + 1, nxt) if j != i):
                        drop = list(range(hj, nxt))
                edits += [(j, "del", None) for j in drop]
                note = f"{c.key} {('Wave ' + wave_n) if wave_n else 'wave entry'} → Shipped ✓"
            elif len(hits) > 1:
                self.warn(f"{len(hits)} wave-plan lines name {c.key} — wave plan left as is; remove the entry by hand")
        label = f"Wave {wave_n}; " if wave_n else ""
        entry = f"- {c.key} — {self.h.get('shipped') or 'shipped'} *({label}{stamp})*"
        if ship:
            s, e = ship[1] - 1, ship[2]
            body = range(s, min(e, len(lines)))
            if any(re.match(rf"^(- |\| ?){re.escape(c.key)}([^0-9]|$)", lines[i]) for i in body):
                note = note or f"{c.key} already in Shipped"
            elif any(lines[i].lstrip().startswith("|") for i in body):
                self.warn("## Shipped is a table — add the story's row by hand")
            else:
                pos = max([i for i in body if lines[i].strip()] or [s]) + 1
                edits.append((pos, "ins", [entry] if pos - 1 > s else ["", entry]))
                note = note or f"{c.key} → Shipped ✓"
        else:
            while lines and not lines[-1].strip():
                lines.pop()
            lines += ["", "## Shipped", "", entry, ""]
            note = note or f"{c.key} → Shipped ✓ (section created)"
        for i, op, val in sorted(edits, key=lambda x: (x[0], x[1] == "del"), reverse=True):
            if op == "del":
                del lines[i]
            else:
                lines[i:i] = val
        path.write_text("\n".join(lines))
        self.row("Wave plan", f"{epic} — {note}")

    def close_epic(self, epic):
        try:
            rows = json.loads(self.c.plans("board", "--jql", f"parent = {epic} AND statusCategory != Done") or "[]")
        except RuntimeError as e:
            self.warn(f"epic close not checked — {e}")
            return
        if rows:
            self.row("Epic", f"{epic} — {len(rows)} children still open")
        elif self.move(epic, DONE):
            self.res["epicClosed"] = True
            self.row("Epic", f"{epic} → Done (last story shipped)")

    def sweep_plan_files(self):
        d = Path(self.c.root, ".claude", "plans")
        tok, gone = token(self.c.key), []
        for f in sorted(d.glob("*")) if d.is_dir() else []:
            if f.is_file():
                text = f.read_text(errors="ignore")
                if tok.search(text) or self.c.branch in text:
                    f.unlink()
                    gone.append(f.name)
        if gone:
            self.warn(f"removed .claude/plans/ files: {', '.join(gone)}")

    def plans_commit(self, subject):
        c = self.c
        if not c.plans_repo:
            return
        git("-C", c.plans_repo, "add", f"{c.board}/")
        if git("-C", c.plans_repo, "diff", "--cached", "--quiet")[0] == 0:
            self.row("Plans", "nothing to commit")
            return
        rc, out, err = sh(["git", "-C", c.plans_repo, "commit", "-q", "-m", subject, "-m", self.trailer])
        if rc:
            self.row("Plans", f"NOT committed — {tail(err or out, 3)}")
            return
        if c.auto_push:
            self.row("Plans", "committed (the repo pushes itself)")
        else:
            rc, _, err = git("-C", c.plans_repo, "push", "-q")
            self.row("Plans", "committed · pushed" if not rc else f"committed · NOT pushed — {tail(err, 2)}")

    def secrets(self):
        approved = self.h.get("secrets") or []
        if not approved:
            return
        out = []
        for r in approved:
            repo, paths = expand(r["repo"], self.c.root), r.get("paths") or []
            name = os.path.basename(repo)
            if not paths:
                out.append(f"{name} clean")
                continue
            real = os.path.realpath(repo)
            try:
                if git("-C", real, "rev-parse", "--abbrev-ref", "HEAD")[1] != self.c.main:
                    raise RuntimeError(f"not on {self.c.main}")
                if self.c.require_private and sh(["gh", "repo", "view", "--json", "visibility", "-q", ".visibility"],
                                                 cwd=real)[1] != "PRIVATE":
                    raise RuntimeError("GitHub visibility is not PRIVATE")
                for step in (["pull", "-q", "--ff-only"], ["add", "--", *paths],
                             ["commit", "-q", "-m", f"chore: {self.c.key} commit pending secrets", "-m", self.trailer],
                             ["push", "-q", "origin", self.c.main]):
                    rc, o, e = git("-C", real, *step)
                    if rc:
                        raise RuntimeError(f"git {step[0]} failed — {tail(e or o, 2)}")
                out.append(f"{name} {git('-C', real, 'rev-parse', '--short', 'HEAD')[1]} pushed")
            except RuntimeError as e:
                out.append(f"{name} NOT pushed — {e}")
        self.row("Secrets", " · ".join(out))

    def storybook(self):
        if self.h.get("keepStorybook"):
            self.row("Storybook", "left running (--keep-storybook)")
            return
        rc, out, err = sh(["sh", str(HERE / "stop-storybook.sh")], cwd=self.c.root)
        lines = (out or err).splitlines()
        self.row("Storybook", lines[0] if lines else "nothing to stop")
        self.rows += [f"{'':11}{line}" for line in lines[1:]]

    def notify(self, task):
        if not self.h.get("notify") or not self.c.notify:
            return
        sh(f"{os.path.expanduser(self.c.notify)} {shlex.quote(f'{self.c.key} · {task}')}", cwd=self.c.root, shell=True)

    def next_story(self, epic):
        c = self.c
        if not self.h.get("nextStory") or not c.jql:
            return
        try:
            todo = json.loads(c.plans("board", "--jql", c.jql) or "[]")
        except RuntimeError as e:
            self.warn(f"next story not looked up — {e}")
            return
        if not todo:
            self.row("Next", f"none — {c.done_msg}")
            return
        pick, group = None, None
        if c.ordering != "jql":
            try:
                text = c.plans("section", epic, "Wave").splitlines()
            except RuntimeError:
                text = []
            heads = any(line.startswith("### ") for line in text)
            seen = not heads
            for line in text:
                m = re.match(rf"^###\s.*?\b(?:Wave|{re.escape(c.group)})\s+(\d+)", line, re.I)
                if line.startswith("### "):
                    seen, group = True, (m.group(1) if m else group)
                if seen and ITEM.match(line):
                    pick = next((t for t in todo if token(t["key"]).search(line)), None)
                    if pick:
                        break
        pick = pick or todo[0]
        self.res["next"] = pick["key"]
        where = f" ({c.group} {group})" if group else ""
        self.row("Next", f"{pick['key']} — {pick.get('summary')}{where} → /giga-workflow:epic-next {c.board}")
        try:
            plan = c.plans("ensure", pick["key"])
            effort = next((line.split(":", 1)[1].strip() for line in Path(plan).read_text().splitlines()
                           if line.startswith("effort:")), None)
            if effort:
                self.row("Effort", f"{effort} — run `/effort {effort}` before /giga-workflow:epic-next")
        except (RuntimeError, OSError):
            pass

    # -- the run

    def run(self):
        c, h = self.c, self.h
        if c.branch in (c.main, "master"):
            raise Stop("preflight", f"on {c.branch} — never ship from the base branch", "nothing done")
        self.build()
        sk = c.skills()
        if sk and sk["pending"]:
            self.land_skills(sk)
        elif sk and sk["landed"]:
            self.res["skillsSha"] = sk["landed"]
        sha = self.commit()
        self.res["sha"] = sha
        skill_only = sha is None
        if skill_only and not self.res["skillsSha"]:
            raise Stop("commit", "nothing to commit and no skills leg", "nothing done")
        if h.get("noPush"):
            return f"committed locally (--no-push) — run without --no-push to land {c.key}"
        sk_par = f"Skills: `{self.res['skillsSha']}` on `{c.sk_branch}` ({c.sk_name})." if self.res["skillsSha"] else ""
        epic = self.story_epic()
        follow = h.get("followUps") or []
        audit = h.get("auditKeys") or []
        suffix = (f" + follow-ups {', '.join(follow)}" if follow else "") + (f" · audit {', '.join(audit)}" if audit else "")
        done_stamp = None

        if skill_only:
            self.res["ticket"] = self.move(c.key, DONE)
            self.row("Ticket", f"{c.key} → {self.res['ticket'] or 'unchanged'}")
            self.subtasks()
            self.comment(f"Landed on {c.sk_branch}", [sk_par])
            self.outcome(f"{c.sk_name} {self.res['skillsSha']}")
            headline = f"landed on {c.sk_branch} + Done"
            done_stamp = f"{c.sk_name} {self.res['skillsSha']}" if c.mode != "epic-branch" else None
            remove_wave = c.mode != "epic-branch"
            if c.mode == "epic-branch":
                self.shipped_line(epic, f"{c.sk_name} {self.res['skillsSha']}", remove_wave=False)
        elif c.mode == "epic-branch":
            self.land_epic_branch()
            self.res["ticket"] = self.move(c.key, DONE)
            self.row("Ticket", f"{c.key} → {self.res['ticket'] or 'unchanged'}")
            self.subtasks()
            self.comment("Committed on epic branch",
                         [f"Commit: `{sha}` on branch `{c.epic_branch}` (epic `{c.epic}`).", sk_par])
            self.outcome(f"{sha}" + (f" · {c.sk_name} {self.res['skillsSha']}" if self.res["skillsSha"] else ""))
            self.shipped_line(epic, sha, remove_wave=False)
            headline = "committed on the epic branch + Done"
        elif c.mode == "direct":
            sha = self.land_direct()
            self.res["sha"] = sha
            self.res["ticket"] = self.move(c.key, DONE)
            self.row("Ticket", f"{c.key} → {self.res['ticket'] or 'unchanged'}")
            self.subtasks()
            self.comment(f"Merged to `{c.main}`", [f"Commit: `{sha}` on `{c.main}` (epic `{c.epic}`).", sk_par])
            self.outcome(sha + (f" · {c.sk_name} {self.res['skillsSha']}" if self.res["skillsSha"] else ""))
            headline, done_stamp, remove_wave = f"merged to {c.main} + Done", sha, True
        else:
            pr = self.push_pr()
            review = self.move(c.key, REVIEW)
            self.subtasks()
            label = f"PR #{pr['number']}" + (f" · {c.sk_name} {self.res['skillsSha']}" if self.res["skillsSha"] else "")
            if self.until == "review":
                self.row("PR", f"#{pr['number']} — {pr['url']}")
                self.row("Ticket", f"{c.key} → {review or 'unchanged (no review state reachable)'}")
                self.comment("In Review", [f"PR: [{pr['url']}]({pr['url']})",
                                           f"Commit: `{sha}` on branch `{c.branch}` (epic `{c.epic}`).", sk_par])
                self.outcome(label)
                self.res["ticket"] = review
                headline = "ready for review"
            else:
                msha = self.merge(pr)
                self.res["ticket"] = self.move(c.key, DONE)
                self.row("Ticket", f"{c.key} → {' → '.join(x for x in (review, self.res['ticket']) if x) or 'unchanged'}")
                self.comment("Merged", [f"PR: [{pr['url']}]({pr['url']})",
                                        f"Commit: `{msha}` on `{c.main}` (epic `{c.epic}`).", sk_par])
                self.outcome(label)
                headline, done_stamp, remove_wave = f"shipped — merged on {c.main} + Done", f"PR #{pr['number']}", True

        if done_stamp:
            self.shipped_line(epic, done_stamp, remove_wave=remove_wave)
            self.close_epic(epic)
            self.sweep_plan_files()
        self.plans_commit(f"docs({c.board}): {c.key} {'shipped' if done_stamp or c.mode == 'epic-branch' else 'outcome'}{suffix}")
        if done_stamp:
            self.secrets()
        self.storybook()
        notes = {"ready for review": f"story complete — PR #{self.res['pr']} ready for review",
                 "committed on the epic branch + Done": "story complete — committed on epic branch + Done"}
        self.notify(notes.get(headline) or (f"story shipped — PR #{self.res['pr']} merged + Done" if self.res["pr"]
                                            else f"story complete — {headline}"))
        if done_stamp:
            self.next_story(epic)
        return headline


def main(argv):
    if len(argv) >= 3 and argv[0] == "preflight":
        try:
            return preflight(argv[1], argv[2], "--secrets" in argv)
        except Stop as s:
            print(f"Refuse:      {s.reason}")
            return 1
    if len(argv) == 2 and argv[0] == "run":
        handoff = json.loads(Path(argv[1]).read_text())
        try:
            ship = Ship(handoff)
        except Stop as s:
            print(f"STOPPED at {s.stage}: {s.reason}\nState: {s.state}")
            return 1
        stop = None
        try:
            print(f"✓ Story {ship.c.key} {ship.run()}")
        except Stop as s:
            stop = s
            ship.res["stopped"] = s.stage
            print(f"✗ Story {ship.c.key} stopped at {s.stage}")
        print("\n".join(ship.rows))
        for w in ship.warns:
            print(f"! {w}")
        if stop:
            print(f"STOPPED at {stop.stage}: {stop.reason}\nState: {stop.state}")
        print("RESULT " + json.dumps(ship.res))
        return 1 if stop else 0
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
