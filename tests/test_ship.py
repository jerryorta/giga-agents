import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHIP = REPO / "plugins/giga-workflow/skills/epic-story-complete/scripts/ship.py"

FAKE_PLANS = textwrap.dedent(r'''
    import json, os, re, sys
    from pathlib import Path
    STATE, ROOT = Path(os.environ["FAKE_STATE"]), Path(os.environ["FAKE_PLANS_ROOT"])
    st = json.loads(STATE.read_text())
    cmd, args = sys.argv[1], sys.argv[2:]
    def save(): STATE.write_text(json.dumps(st))
    def plan(key): return ROOT / key.split("-")[0].lower() / f"{key}.md"
    if cmd == "ensure":
        print(plan(args[0]))
    elif cmd == "section":
        p = plan(args[0]); lines = p.read_text().split("\n"); start = end = None
        for i, line in enumerate(lines):
            if line.startswith("## "):
                if start is not None: end = i; break
                if line[3:].lower().startswith(args[1].lower()): start = i + 1
        if start is None: print(p, file=sys.stderr); sys.exit(1)
        end = end if end is not None else len(lines)
        if "--range" in args: print(p, start, end)
        else: print("\n".join(lines[start - 1:end]))
    elif cmd == "board":
        jql, issues = args[1], st["issues"]
        m = re.match(r"key = (\S+) OR parent = (\S+)", jql)
        if m: rows = [k for k, v in issues.items() if k == m[1] or v.get("parent") == m[1]]
        elif (m := re.match(r"parent = (\S+) AND statusCategory != Done", jql)):
            rows = [k for k, v in issues.items() if v.get("parent") == m[1] and v["status"] != "Done"]
        elif (m := re.match(r'parent = (\S+) AND status = "To Do"', jql)):
            rows = [k for k, v in issues.items() if v.get("parent") == m[1] and v["status"] == "To Do"]
        else: sys.exit(f"unknown jql {jql}")
        print(json.dumps([dict(key=k, status=issues[k]["status"], category="", type=issues[k].get("type", "Story"),
                               priority="", parent=issues[k].get("parent"), summary=issues[k].get("summary", ""))
                          for k in rows]))
    elif cmd == "transition":
        key, names = args[0], args[1:]
        i = st["issues"][key]
        if i["status"].lower() not in [n.lower() for n in names]:
            i["status"] = names[0]; save()
        print(i["status"])
    elif cmd == "comment":
        st["comments"].append({"key": args[0], "body": sys.stdin.read()}); save(); print("1000")
''')

FAKE_GH = textwrap.dedent(r'''
    import json, os, subprocess, sys
    from pathlib import Path
    STATE = Path(os.environ["FAKE_STATE"])
    st = json.loads(STATE.read_text()); a = sys.argv[1:]
    def save(): STATE.write_text(json.dumps(st))
    def git(*x): return subprocess.run(["git", "-C", st["origin"], *x], capture_output=True, text=True).stdout.strip()
    if a[:2] == ["pr", "list"]:
        head = a[a.index("--head") + 1]
        print(json.dumps([{"number": p["number"], "url": p["url"], "state": p["state"]} for p in st["prs"] if p["head"] == head]))
    elif a[:2] == ["pr", "create"]:
        n = len(st["prs"]) + 1; url = f"https://github.test/o/r/pull/{n}"
        st["prs"].append({"number": n, "url": url, "state": "OPEN", "head": a[a.index("--head") + 1],
                          "body": sys.stdin.read(), "mss": st.get("mss", ["CLEAN"])}); save(); print(url)
    elif a[:2] == ["pr", "view"]:
        p = st["prs"][int(a[2]) - 1]
        mss = p["mss"].pop(0) if len(p["mss"]) > 1 else p["mss"][0]; save()
        print(json.dumps({"state": p["state"], "mergeStateStatus": mss, "mergedAt": p.get("mergedAt"),
                          "mergeCommit": {"oid": p.get("oid", "")}}))
    elif a[:2] == ["pr", "merge"]:
        p = st["prs"][int(a[2]) - 1]
        git("update-ref", "refs/heads/main", f"refs/heads/{p['head']}")
        p.update(state="MERGED", mergedAt="2026-11-18T00:00:00Z", oid=git("rev-parse", "main"))
        git("update-ref", "-d", f"refs/heads/{p['head']}"); save()
    elif a[:2] == ["pr", "update-branch"]:
        pass
    elif a[:2] == ["repo", "view"]:
        print("PRIVATE")
    else:
        sys.exit(f"fake gh: unhandled {a}")
''')

EPIC = """---
jira: ABC-100
---
# ABC-100 — Epic

## Wave Plan

### Wave 1 — first
- ABC-1 — first story · Story
- ABC-2 — second story · Story

## Shipped
"""


class ShipTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@example.com", SHIP_POLL_SECONDS="0",
                        FAKE_STATE=str(self.tmp / "state.json"), FAKE_PLANS_ROOT=str(self.tmp / "plans"))
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(f"#!/bin/sh\nexec python3 {self.tmp / 'gh.py'} \"$@\"\n")
        (bin_dir / "gh").chmod(0o755)
        (self.tmp / "gh.py").write_text(FAKE_GH)
        (self.tmp / "plans.py").write_text(FAKE_PLANS)
        self.env["PATH"] = f"{bin_dir}:{self.env['PATH']}"
        self.origin, self.work, self.plans = self.tmp / "origin.git", self.tmp / "work", self.tmp / "plans"
        self.git("init", "-q", "--bare", "-b", "main", str(self.origin), cwd=self.tmp)
        self.git("clone", "-q", str(self.origin), str(self.work), cwd=self.tmp)
        (self.work / "a.txt").write_text("one\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        self.git("push", "-q", "origin", "HEAD:main")
        (self.plans / "abc").mkdir(parents=True)
        (self.plans / "abc/ABC-1.md").write_text("---\njira: ABC-1\nepic: ABC-100\n---\n# ABC-1\n\n## Acceptance\n- x\n")
        (self.plans / "abc/ABC-2.md").write_text("---\njira: ABC-2\nepic: ABC-100\neffort: high\n---\n# ABC-2\n")
        (self.plans / "abc/ABC-100.md").write_text(EPIC)
        self.git("init", "-q", "-b", "main", cwd=self.plans)
        self.git("add", "-A", cwd=self.plans)
        self.git("commit", "-q", "-m", "init", cwd=self.plans)
        self.state({"origin": str(self.origin), "prs": [], "comments": [], "issues": {
            "ABC-1": {"status": "In Progress", "parent": "ABC-100", "summary": "first story"},
            "ABC-2": {"status": "To Do", "parent": "ABC-100", "summary": "second story"},
            "ABC-100": {"status": "In Progress", "type": "Epic"}}})

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.work, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def state(self, value=None):
        f = self.tmp / "state.json"
        if value is not None:
            f.write_text(json.dumps(value))
        return json.loads(f.read_text())

    def board(self, mode="pr", name="abc"):
        giga = self.work / ".claude/giga"
        giga.mkdir(parents=True, exist_ok=True)
        (giga / "config.json").write_text(json.dumps({"workflow": {
            "plans": {"repo": str(self.plans), "script": str(self.tmp / "plans.py"), "autoPush": True}}}))
        (giga / f"epic.{name}.json").write_text(json.dumps({
            "epicKey": "ABC-100", "mergeMode": mode, "jql": 'parent = ABC-100 AND status = "To Do"',
            "groupLabel": "Wave", "completionMessage": "All done"}))
        (self.work / ".git/info/exclude").write_text(".claude/\n")

    def story(self):
        self.git("checkout", "-q", "-b", "feat/abc-1-first")
        (self.work / "a.txt").write_text("two\n")

    def ship(self, until="merged", board="abc", **extra):
        handoff = {"board": board, "key": "ABC-1", "until": until, "nextStory": True,
                   "commit": {"subject": "feat(web): ABC-1 do the first thing", "trailer": "Co-Authored-By: t"},
                   "prBody": "## Summary\n- x\n", "shipped": "did the first thing",
                   "outcome": {"text": "It shipped.", "pins": ["x holds — pinned by `a.spec.ts`"]}, **extra}
        f = self.tmp / "handoff.json"
        f.write_text(json.dumps(handoff))
        p = subprocess.run(["python3", str(SHIP), "run", str(f)], cwd=self.work, env=self.env,
                           capture_output=True, text=True)
        result = json.loads(p.stdout.rsplit("RESULT ", 1)[1]) if "RESULT " in p.stdout else {}
        return p.returncode, p.stdout + p.stderr, result

    def test_pr_merged_ships_to_done(self):
        self.board()
        self.story()
        code, out, res = self.ship()
        self.assertEqual(code, 0, out)
        self.assertEqual((res["pr"], res["ticket"], res["next"]), (1, "Done", "ABC-2"))
        st = self.state()
        self.assertTrue(st["comments"][0]["body"].startswith("### Merged"))
        self.assertEqual(self.git("rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertEqual(self.git("show", "origin/main:a.txt"), "two")
        plan = (self.plans / "abc/ABC-1.md").read_text()
        self.assertIn("## Outcome — shipped (PR #1)\n\nIt shipped.\n\n### Pinned\n\n- x holds", plan)
        epic = (self.plans / "abc/ABC-100.md").read_text()
        self.assertNotIn("- ABC-1 — first story", epic)
        self.assertIn("### Wave 1 — first\n- ABC-2", epic)
        self.assertIn("## Shipped\n\n- ABC-1 — did the first thing *(Wave 1; PR #1)*", epic)
        self.assertEqual(self.git("log", "-1", "--format=%s", cwd=self.plans), "docs(abc): ABC-1 shipped")
        self.assertIn("Effort:    high", out)

    def test_board_name_differs_from_key_prefix(self):
        self.board(name="abc2")
        self.story()
        code, out, res = self.ship(board="abc2")
        self.assertEqual(code, 0, out)
        self.assertIn("abc/ABC-1.md § Outcome", out)
        self.assertEqual(self.git("log", "-1", "--format=%s", cwd=self.plans), "docs(abc): ABC-1 shipped")
        self.assertEqual(self.git("status", "--short", cwd=self.plans), "")

    def test_pr_review_stops_at_in_review(self):
        self.board()
        self.story()
        code, out, res = self.ship(until="review")
        self.assertEqual(code, 0, out)
        self.assertEqual(res["ticket"], "In Review")
        self.assertEqual(self.state()["prs"][0]["state"], "OPEN")
        self.assertIn("## Outcome — shipped (PR #1)", (self.plans / "abc/ABC-1.md").read_text())
        self.assertIn("- ABC-1 — first story", (self.plans / "abc/ABC-100.md").read_text())
        self.assertEqual(self.git("log", "-1", "--format=%s", cwd=self.plans), "docs(abc): ABC-1 outcome")

    def test_unknown_then_clean_merges(self):
        self.board()
        self.story()
        st = self.state()
        st["mss"] = ["UNKNOWN", "UNKNOWN", "CLEAN"]
        self.state(st)
        code, out, res = self.ship()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.state()["prs"][0]["state"], "MERGED")

    def test_dirty_stops_before_cleanup(self):
        self.board()
        self.story()
        st = self.state()
        st["mss"] = ["DIRTY"]
        self.state(st)
        code, out, res = self.ship()
        self.assertEqual(code, 1)
        self.assertEqual(res["stopped"], "merge")
        self.assertIn("mergeStateStatus=DIRTY", out)
        self.assertEqual(self.state()["issues"]["ABC-1"]["status"], "In Review")
        self.assertIn("- ABC-1 — first story", (self.plans / "abc/ABC-100.md").read_text())

    def test_hook_failure_then_rerun_resumes(self):
        self.board()
        self.story()
        hook = self.work / ".git/hooks/pre-commit"
        hook.write_text(f"#!/bin/sh\n[ -e {self.tmp}/block ] && echo 'lint failed' && exit 1\nexit 0\n")
        hook.chmod(0o755)
        (self.tmp / "block").write_text("")
        code, out, res = self.ship()
        self.assertEqual((code, res["stopped"]), (1, "commit"), out)
        self.assertIn("lint failed", out)
        (self.tmp / "block").unlink()
        code, out, res = self.ship()
        self.assertEqual(code, 0, out)
        self.assertEqual(res["ticket"], "Done")

    def test_direct_fast_forwards_main(self):
        self.board("direct")
        self.story()
        code, out, res = self.ship(until="review")
        self.assertEqual(code, 0, out)
        self.assertIsNone(res["pr"])
        self.assertEqual(self.git("show", "origin/main:a.txt"), "two")
        self.assertNotIn("feat/abc-1-first", self.git("branch"))
        epic = (self.plans / "abc/ABC-100.md").read_text()
        self.assertIn(f"*(Wave 1; {res['sha']})*", epic)

    def test_last_story_closes_the_epic(self):
        self.board()
        self.story()
        st = self.state()
        st["issues"]["ABC-2"]["status"] = "Done"
        self.state(st)
        code, out, res = self.ship()
        self.assertEqual(code, 0, out)
        self.assertTrue(res["epicClosed"])
        self.assertEqual(self.state()["issues"]["ABC-100"]["status"], "Done")
        self.assertIn("Next:      none — All done", out)

    def test_preflight_refuses_on_main(self):
        self.board()
        p = subprocess.run(["python3", str(SHIP), "preflight", "abc", "ABC-1"], cwd=self.work, env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn("never runs on the base branch", p.stdout)


if __name__ == "__main__":
    unittest.main()
