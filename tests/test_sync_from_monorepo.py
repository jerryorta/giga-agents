import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("sync_from_monorepo", REPO / "scripts" / "sync_from_monorepo.py")
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)

FORBIDDEN = json.loads((REPO / "sync.json").read_text())["forbidden"]

OWNER = {
    "ux-design": "giga-ux",
    "ux-reviewer": "giga-ux",
    "jira": "giga-workflow",
    "create-jira": "giga-workflow",
    "epic-next": "giga-workflow",
    "epic-loop": "giga-workflow",
    "epic-story-complete": "giga-workflow",
    "epic-story-ship": "giga-workflow",
    "dev-server": "giga-workflow",
}

SAMPLES = {
    "/Users/": ["cd /Users/someone/Dev/app"],
    "@gigasoftware\\.io": ["mail someone@gigasoftware.io"],
    "claude\\.ai/(code/)?artifact/": ["https://claude.ai/artifact/abc123", "https://claude.ai/code/artifact/abc123"],
    "atlassian\\.net": ["https://example.atlassian.net/browse/ABC-1"],
    "[a-z]+_secrets\\b": ["read ~/Dev/acme_secrets/jira.json"],
    "github_pat_|ghp_[A-Za-z0-9]|ATATT": ["GH_TOKEN=github_pat_abc", "GH_TOKEN=ghp_abc", "token: ATATTexample"],
}


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class OwnersTest(unittest.TestCase):
    def test_maps_every_skill_and_agent_to_its_plugin(self):
        plugins = {
            "giga-ux": {"skills": ["ux-design"], "agents": ["ux-reviewer", "ux-blind-user"]},
            "giga-workflow": {"skills": ["jira", "epic-next"]},
        }
        self.assertEqual(sync.owners(plugins), {
            "ux-design": "giga-ux",
            "ux-reviewer": "giga-ux",
            "ux-blind-user": "giga-ux",
            "jira": "giga-workflow",
            "epic-next": "giga-workflow",
        })


class NamespaceTest(unittest.TestCase):
    def ns(self, text: str) -> str:
        return sync.namespace(text, OWNER)

    def test_prefixes_backticked_names_with_their_owning_plugin_across_plugins(self):
        self.assertEqual(self.ns("Dispatch `ux-reviewer`, then run `jira`."),
                         "Dispatch `giga-ux:ux-reviewer`, then run `giga-workflow:jira`.")

    def test_prefixes_invocations_wherever_they_stand(self):
        cases = {
            "/epic-next arch": "/giga-workflow:epic-next arch",
            "then /jira ABC-1": "then /giga-workflow:jira ABC-1",
            "`/jira ABC-1`": "`/giga-workflow:jira ABC-1`",
            "(run /ux-design first)": "(run /giga-ux:ux-design first)",
            "Finish with /epic-story-ship.": "Finish with /giga-workflow:epic-story-ship.",
            "/jira, then /epic-loop": "/giga-workflow:jira, then /giga-workflow:epic-loop",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.ns(text), expected)

    def test_leaves_path_segments_and_urls_alone(self):
        for text in (
            "skills/jira",
            "plugins/giga-workflow/skills/jira/SKILL.md",
            "${CLAUDE_SKILL_DIR}/../epic-loop/autonomy-contract.md",
            "https://example.com/jira",
            "~/jira",
            "./jira",
            ".claude/giga/epic.<board>.json",
            ".claude/giga/epic-loop.json",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.ns(text), text)

    def test_never_prefixes_a_name_twice(self):
        for text in ("`giga-ux:ux-design`", "/giga-workflow:jira ABC-1", "`/giga-workflow:epic-next`"):
            with self.subTest(text=text):
                self.assertEqual(self.ns(text), text)

    def test_is_idempotent(self):
        once = self.ns("Run /epic-next, dispatch `ux-reviewer`, read skills/jira/SKILL.md.")
        self.assertEqual(self.ns(once), once)

    def test_a_longer_name_wins_over_its_prefix(self):
        owner = {**OWNER, "epic-story": "giga-other"}
        cases = {
            "/epic-story-complete": "/giga-workflow:epic-story-complete",
            "/epic-story-ship": "/giga-workflow:epic-story-ship",
            "`epic-story-ship`": "`giga-workflow:epic-story-ship`",
            "/epic-story": "/giga-other:epic-story",
            "/epic-story-draft": "/epic-story-draft",
            "/create-jira": "/giga-workflow:create-jira",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(sync.namespace(text, owner), expected)


class NamespacePreloadsTest(unittest.TestCase):
    def test_prefixes_owned_skills_in_the_front_matter_only(self):
        agent = (
            "---\n"
            "name: ux-reviewer\n"
            "skills:\n"
            "  - ux-design\n"
            "  - claude-in-chrome\n"
            "  - giga-workflow:dev-server\n"
            "---\n"
            "Steps:\n"
            "  - ux-design\n"
        )
        self.assertEqual(sync.namespace_preloads(agent, OWNER), (
            "---\n"
            "name: ux-reviewer\n"
            "skills:\n"
            "  - giga-ux:ux-design\n"
            "  - claude-in-chrome\n"
            "  - giga-workflow:dev-server\n"
            "---\n"
            "Steps:\n"
            "  - ux-design\n"
        ))

    def test_leaves_text_without_front_matter_alone(self):
        text = "Steps:\n  - ux-design\n"
        self.assertEqual(sync.namespace_preloads(text, OWNER), text)


class BuildPluginTest(unittest.TestCase):
    def test_rewrites_markdown_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp, "src"), Path(tmp, "out")
            script = "#!/bin/sh\n# see /epic-next and `ux-design`\n"
            config = '{"next": "/epic-next"}\n'
            write(src / ".claude/skills/jira/SKILL.md", "Then run /epic-next.\n")
            write(src / ".claude/skills/jira/scripts/run.sh", script)
            write(src / ".claude/skills/jira/config.json", config)

            sync.build_plugin(src, out, {"skills": ["jira"]}, OWNER)

            self.assertEqual((out / "skills/jira/SKILL.md").read_text(), "Then run /giga-workflow:epic-next.\n")
            self.assertEqual((out / "skills/jira/scripts/run.sh").read_text(), script)
            self.assertEqual((out / "skills/jira/config.json").read_text(), config)


class LeaksTest(unittest.TestCase):
    def test_every_forbidden_pattern_has_a_sample(self):
        self.assertCountEqual(SAMPLES, FORBIDDEN)

    def test_every_forbidden_pattern_fires_on_its_samples(self):
        for pattern, samples in SAMPLES.items():
            for sample in samples:
                with self.subTest(pattern=pattern, sample=sample), tempfile.TemporaryDirectory() as tmp:
                    write(Path(tmp, "skills/x/SKILL.md"), f"Intro.\n{sample}\n")
                    self.assertEqual(sync.leaks(Path(tmp), [pattern]),
                                     [f"skills/x/SKILL.md:2: matches {pattern!r}"])

    def test_stays_quiet_on_the_readme_example_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(REPO / "README.md", Path(tmp, "README.md"))
            self.assertEqual(sync.leaks(Path(tmp), FORBIDDEN), [])


class MainTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name, "marketplace")
        self.src = Path(tmp.name, "monorepo")
        write(self.root / "sync.json", json.dumps({
            "source": str(self.src),
            "plugins": {
                "giga-ux": {"skills": ["ux-design"], "agents": ["ux-reviewer"]},
                "giga-workflow": {"skills": ["jira"]},
            },
            "forbidden": FORBIDDEN,
        }))
        write(self.root / "plugins/giga-ux/.claude-plugin/plugin.json", '{"name": "giga-ux"}\n')
        write(self.root / "plugins/giga-workflow/skills/retired/SKILL.md", "Retired.\n")
        write(self.src / ".claude/skills/ux-design/SKILL.md", "Hand off to /jira.\n")
        write(self.src / ".claude/skills/jira/SKILL.md", "Dispatch `ux-reviewer`; its files live in skills/jira/.\n")
        write(self.src / ".claude/skills/jira/scripts/stop.sh", "# called by /jira\n")
        write(self.src / ".claude/agents/ux-reviewer.md",
              "---\nname: ux-reviewer\nskills:\n  - ux-design\n---\nThen /jira.\n")

    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with (mock.patch.object(sync, "ROOT", self.root),
              mock.patch.object(sys, "argv", ["sync_from_monorepo.py", *args]),
              contextlib.redirect_stdout(out),
              contextlib.redirect_stderr(err)):
            code = sync.main()
        return code, out.getvalue(), err.getvalue()

    def plugins(self) -> dict[str, str]:
        base = self.root / "plugins"
        return {p.relative_to(base).as_posix(): p.read_text() for p in sorted(base.rglob("*")) if p.is_file()}

    def test_dry_run_checks_and_writes_nothing(self):
        before = self.plugins()
        code, out, err = self.run_main("--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out, "checked giga-ux: 1 skills, 1 agents\nchecked giga-workflow: 1 skills, 0 agents\n")
        self.assertEqual(err, "")
        self.assertEqual(self.plugins(), before)

    def test_sync_writes_the_namespaced_plugins(self):
        code, out, err = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(out, "synced giga-ux: 1 skills, 1 agents\nsynced giga-workflow: 1 skills, 0 agents\n")
        self.assertEqual(err, "")
        self.assertEqual(self.plugins(), {
            "giga-ux/.claude-plugin/plugin.json": '{"name": "giga-ux"}\n',
            "giga-ux/agents/ux-reviewer.md": "---\nname: ux-reviewer\nskills:\n  - giga-ux:ux-design\n---\nThen /giga-workflow:jira.\n",
            "giga-ux/skills/ux-design/SKILL.md": "Hand off to /giga-workflow:jira.\n",
            "giga-workflow/skills/jira/SKILL.md": "Dispatch `giga-ux:ux-reviewer`; its files live in skills/jira/.\n",
            "giga-workflow/skills/jira/scripts/stop.sh": "# called by /jira\n",
        })

    def test_a_leak_fails_and_writes_nothing(self):
        write(self.src / ".claude/skills/jira/SKILL.md", "Intro.\nSee /Users/someone/notes.\n")
        before = self.plugins()
        for args in (("--dry-run",), ()):
            with self.subTest(args=args):
                code, out, err = self.run_main(*args)
                self.assertEqual(code, 1)
                self.assertEqual(out, "")
                self.assertIn("Refusing to publish", err)
                self.assertIn("giga-workflow/skills/jira/SKILL.md:2: matches '/Users/'", err)
                self.assertEqual(self.plugins(), before)


if __name__ == "__main__":
    unittest.main()
