import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_plugins", REPO / "scripts" / "check_plugins.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

FORBIDDEN = check.FORBIDDEN
PLUGINS = REPO / "plugins"

OWNER = {
    "ux-design": "giga-ux",
    "ux-reviewer": "giga-ux",
    "jira": "giga-workflow",
    "epic-next": "giga-workflow",
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


def real_plugins() -> list[Path]:
    return sorted(p for p in PLUGINS.iterdir() if p.is_dir())


class OwnersTest(unittest.TestCase):
    def test_derives_every_skill_and_agent_from_the_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp)
            write(plugins / "giga-ux/skills/ux-design/SKILL.md", "x")
            write(plugins / "giga-ux/agents/ux-reviewer.md", "x")
            write(plugins / "giga-workflow/skills/jira/SKILL.md", "x")
            write(plugins / "giga-workflow/skills/jira/notes.md", "x")
            write(plugins / "giga-standards/hooks/hooks.json", "{}")
            self.assertEqual(check.owners(plugins), {
                "ux-design": "giga-ux",
                "ux-reviewer": "giga-ux",
                "jira": "giga-workflow",
            })


class NamespaceTest(unittest.TestCase):
    def ns(self, text: str) -> str:
        return check.namespace(text, OWNER)

    def test_prefixes_backticked_names_and_invocations(self):
        self.assertEqual(self.ns("Dispatch `ux-reviewer`, then /jira ABC-1."),
                         "Dispatch `giga-ux:ux-reviewer`, then /giga-workflow:jira ABC-1.")

    def test_leaves_path_segments_and_urls_alone(self):
        for text in ("skills/jira", "https://example.com/jira", "~/jira", "${CLAUDE_SKILL_DIR}/../epic-next/x.md"):
            with self.subTest(text=text):
                self.assertEqual(self.ns(text), text)

    def test_is_idempotent(self):
        once = self.ns("Run /epic-next, dispatch `ux-reviewer`.")
        self.assertEqual(self.ns(once), once)

    def test_prefixes_preloads_in_the_front_matter_only(self):
        agent = "---\nname: x\nskills:\n  - ux-design\n  - claude-in-chrome\n---\n  - ux-design\n"
        self.assertEqual(check.namespace_preloads(agent, OWNER),
                         "---\nname: x\nskills:\n  - giga-ux:ux-design\n  - claude-in-chrome\n---\n  - ux-design\n")


class BareNamesTest(unittest.TestCase):
    def check(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in files.items():
                write(Path(tmp, "plugins/giga-workflow", rel), text)
            return check.bare_names(Path(tmp, "plugins/giga-workflow"), OWNER)

    def test_flags_a_bare_backticked_name(self):
        self.assertEqual(self.check({"skills/a/SKILL.md": "Intro.\nRun `jira` now.\n"}),
                         ["giga-workflow/skills/a/SKILL.md:2: bare jira"])

    def test_flags_a_bare_invocation(self):
        self.assertEqual(self.check({"skills/a/SKILL.md": "Then /epic-next arch.\n"}),
                         ["giga-workflow/skills/a/SKILL.md:1: bare epic-next"])

    def test_passes_a_namespaced_name(self):
        text = "Run `giga-workflow:jira`, then /giga-workflow:epic-next and /giga-ux:ux-design.\n"
        self.assertEqual(self.check({"skills/a/SKILL.md": text}), [])

    def test_passes_a_path_segment_and_a_url(self):
        text = "Read skills/jira/SKILL.md and https://example.com/jira.\n"
        self.assertEqual(self.check({"skills/a/SKILL.md": text}), [])

    def test_flags_a_bare_preload_in_agent_front_matter(self):
        agent = "---\nname: a\nskills:\n  - ux-design\n---\nBody.\n"
        self.assertEqual(self.check({"agents/a.md": agent}),
                         ["giga-workflow/agents/a.md:1: bare preloaded skill in front matter"])

    def test_passes_a_namespaced_preload(self):
        agent = "---\nname: a\nskills:\n  - giga-ux:ux-design\n---\nBody.\n"
        self.assertEqual(self.check({"agents/a.md": agent}), [])


class LeaksTest(unittest.TestCase):
    def test_every_forbidden_pattern_has_a_sample(self):
        self.assertCountEqual(SAMPLES, FORBIDDEN)

    def test_every_forbidden_pattern_fires_on_its_samples(self):
        for pattern, samples in SAMPLES.items():
            for sample in samples:
                with self.subTest(pattern=pattern, sample=sample), tempfile.TemporaryDirectory() as tmp:
                    write(Path(tmp, "skills/x/SKILL.md"), f"Intro.\n{sample}\n")
                    self.assertEqual(check.leaks(Path(tmp), [pattern]),
                                     [f"skills/x/SKILL.md:2: matches {pattern!r}"])

    def test_reports_a_sample_inside_a_hook_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "hooks/x.sh"), "#!/usr/bin/env bash\ncd /Users/someone/Dev/app\n")
            self.assertEqual(check.leaks(Path(tmp), ["/Users/"]), ["hooks/x.sh:2: matches '/Users/'"])

    def test_stays_quiet_on_the_readme_example_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(REPO / "README.md", Path(tmp, "README.md"))
            self.assertEqual(check.leaks(Path(tmp), FORBIDDEN), [])


class RefsTest(unittest.TestCase):
    REF = "Read ${CLAUDE_SKILL_DIR}/../y/ref.md first.\n"

    def test_flags_a_reference_into_another_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), f"Intro.\n{self.REF}")
            write(Path(tmp, "plugins/b/skills/y/ref.md"), "Ref.\n")
            self.assertEqual(check.broken_refs(Path(tmp, "plugins/a")),
                             ["a/skills/x/SKILL.md:2: y/ref.md is not in a"])

    def test_passes_a_reference_inside_its_own_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), self.REF)
            write(Path(tmp, "plugins/a/skills/y/ref.md"), "Ref.\n")
            self.assertEqual(check.broken_refs(Path(tmp, "plugins/a")), [])

    def test_strips_sentence_punctuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "Then read ${CLAUDE_SKILL_DIR}/../y/ref.md.\n")
            write(Path(tmp, "plugins/a/skills/y/ref.md"), "Ref.\n")
            self.assertEqual(check.broken_refs(Path(tmp, "plugins/a")), [])

    def test_the_published_tree_resolves(self):
        for plugin in real_plugins():
            with self.subTest(plugin=plugin.name):
                self.assertEqual(check.broken_refs(plugin), [])


class PublishedTreeTest(unittest.TestCase):
    def test_no_bare_names(self):
        owner = check.owners(PLUGINS)
        for plugin in real_plugins():
            with self.subTest(plugin=plugin.name):
                self.assertEqual(check.bare_names(plugin, owner), [])

    def test_no_leaks(self):
        self.assertEqual(check.leaks(PLUGINS, FORBIDDEN), [])
        self.assertEqual(check.leaks(REPO / "README.md", FORBIDDEN), [])


if __name__ == "__main__":
    unittest.main()
