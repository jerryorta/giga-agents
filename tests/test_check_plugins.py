import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


def page(*targets: str) -> str:
    """A plugin page whose table has one row linking each target."""
    return "| Skill | Use it to |\n| --- | --- |\n" + "".join(f"| [x]({t}) | y |\n" for t in targets)


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


class PublishedLeaksTest(unittest.TestCase):
    def test_reports_a_sample_under_docs_by_its_repo_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "Intro.\n")
            write(Path(tmp, "docs/plans-repo.md"), "Intro.\ncd /Users/someone/Dev/app\n")
            write(Path(tmp, "README.md"), "Intro.\n")
            self.assertEqual(check.published_leaks(Path(tmp), FORBIDDEN),
                             ["docs/plans-repo.md:2: matches '/Users/'"])

    def test_reports_plugins_and_the_readme_by_their_repo_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "cd /Users/someone/Dev/app\n")
            write(Path(tmp, "README.md"), "Intro.\ncd /Users/someone/Dev/app\n")
            self.assertEqual(check.published_leaks(Path(tmp), ["/Users/"]), [
                "plugins/a/skills/x/SKILL.md:1: matches '/Users/'",
                "README.md:2: matches '/Users/'",
            ])

    def test_stays_quiet_on_a_clean_docs_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "Intro.\n")
            write(Path(tmp, "docs/plans-repo.md"), "Run `python3 <plans.script> ensure ABC-123`.\n")
            self.assertEqual(check.published_leaks(Path(tmp), FORBIDDEN), [])

    def test_skips_a_missing_docs_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "Intro.\n")
            write(Path(tmp, "README.md"), "Intro.\n")
            self.assertEqual(check.published_leaks(Path(tmp), FORBIDDEN), [])

    def test_main_fails_on_a_sample_under_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "Intro.\n")
            write(Path(tmp, "plugins/a/README.md"), page("skills/x/SKILL.md"))
            write(Path(tmp, "docs/plans-repo.md"), "cd /Users/someone/Dev/app\n")
            write(Path(tmp, "README.md"), "Intro.\n")
            err = io.StringIO()
            with mock.patch.object(check, "ROOT", Path(tmp)), contextlib.redirect_stderr(err):
                self.assertEqual(check.main(), 1)
            self.assertEqual(err.getvalue(), "Private content:\n  docs/plans-repo.md:1: matches '/Users/'\n")


class PublishedBareNamesTest(unittest.TestCase):
    def tree(self, tmp: str, docs: str = "Intro.\n", readme: str = "Intro.\n") -> Path:
        write(Path(tmp, "plugins/giga-workflow/skills/jira/SKILL.md"), "Intro.\n")
        write(Path(tmp, "plugins/giga-workflow/README.md"), page("skills/jira/SKILL.md"))
        write(Path(tmp, "docs/guide.md"), docs)
        write(Path(tmp, "README.md"), readme)
        return Path(tmp)

    def main_stderr(self, root: Path) -> tuple[int, str]:
        err = io.StringIO()
        with mock.patch.object(check, "ROOT", root), contextlib.redirect_stderr(err):
            code = check.main()
        return code, err.getvalue()

    def test_reports_a_bare_name_under_docs_by_its_repo_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, docs="Intro.\nThen run /jira ABC-1.\n")
            self.assertEqual(check.published_bare_names(root, OWNER), ["docs/guide.md:2: bare jira"])

    def test_reports_a_bare_name_in_the_readme_by_its_repo_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, readme="Dispatch `ux-reviewer`.\n")
            self.assertEqual(check.published_bare_names(root, OWNER), ["README.md:1: bare ux-reviewer"])

    def test_reports_plugins_by_their_repo_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp)
            write(root / "plugins/giga-workflow/skills/a/SKILL.md", "Then /epic-next arch.\n")
            self.assertEqual(check.published_bare_names(root, OWNER),
                             ["plugins/giga-workflow/skills/a/SKILL.md:1: bare epic-next"])

    def test_reports_a_bare_preload_by_its_repo_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp)
            write(root / "plugins/giga-workflow/agents/a.md", "---\nname: a\nskills:\n  - ux-design\n---\n")
            self.assertEqual(check.published_bare_names(root, OWNER),
                             ["plugins/giga-workflow/agents/a.md:1: bare preloaded skill in front matter"])

    def test_skips_a_missing_docs_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/giga-workflow/skills/jira/SKILL.md"), "Intro.\n")
            write(Path(tmp, "README.md"), "Intro.\n")
            self.assertEqual(check.published_bare_names(Path(tmp), OWNER), [])

    def test_passes_namespaced_names_in_docs_and_the_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = "Run /giga-workflow:jira, then dispatch `giga-ux:ux-reviewer`.\n"
            root = self.tree(tmp, docs=text, readme=text)
            self.assertEqual(check.published_bare_names(root, OWNER), [])

    def test_main_fails_on_a_bare_name_under_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, docs="Then run /jira ABC-1.\n")
            self.assertEqual(self.main_stderr(root), (
                1, "A skill or agent is named without its plugin prefix:\n  docs/guide.md:1: bare jira\n"))

    def test_main_fails_on_a_bare_name_in_the_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.tree(tmp, readme="Intro.\nRun `jira` first.\n")
            self.assertEqual(self.main_stderr(root), (
                1, "A skill or agent is named without its plugin prefix:\n  README.md:2: bare jira\n"))


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


class ArgRefsTest(unittest.TestCase):
    def test_flags_a_digit_after_a_dollar_in_a_skill_and_an_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "Intro.\nawk '{print $0}'\n")
            write(Path(tmp, "plugins/a/agents/y.md"), "Use $1 here.\n")
            self.assertEqual(check.arg_refs(Path(tmp, "plugins"), Path(tmp)), [
                f"plugins/a/agents/y.md:1: matches {check.ARG!r}",
                f"plugins/a/skills/x/SKILL.md:2: matches {check.ARG!r}",
            ])

    def test_passes_other_dollar_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"),
                  "Read ${CLAUDE_SKILL_DIR}/ref.md with $ARGUMENTS.\nwt=$(git rev-parse HEAD) b=$b\n")
            self.assertEqual(check.arg_refs(Path(tmp, "plugins"), Path(tmp)), [])

    def test_ignores_files_claude_code_does_not_substitute(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "Intro.\n")
            write(Path(tmp, "plugins/a/skills/x/scripts/a.sh"), "awk '{print $0}'\n")
            write(Path(tmp, "plugins/a/skills/x/ref.md"), "awk '{print $0}'\n")
            self.assertEqual(check.arg_refs(Path(tmp, "plugins"), Path(tmp)), [])

    def test_main_fails_on_a_digit_after_a_dollar_in_a_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "awk '{print $0}'\n")
            write(Path(tmp, "plugins/a/README.md"), page("skills/x/SKILL.md"))
            write(Path(tmp, "README.md"), "Intro.\n")
            err = io.StringIO()
            with mock.patch.object(check, "ROOT", Path(tmp)), contextlib.redirect_stderr(err):
                self.assertEqual(check.main(), 1)
            self.assertEqual(err.getvalue(),
                             "A skill or agent body holds `$<digit>`, which Claude Code replaces with an argument:\n"
                             f"  plugins/a/skills/x/SKILL.md:1: matches {check.ARG!r}\n")


class UnlistedTest(unittest.TestCase):
    def check(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in files.items():
                write(Path(tmp, "plugins/giga-ux", rel), text)
            return check.unlisted(Path(tmp, "plugins/giga-ux"), Path(tmp))

    def test_passes_a_row_for_every_skill_and_agent(self):
        self.assertEqual(self.check({
            "skills/ux-design/SKILL.md": "x",
            "agents/ux-reviewer.md": "x",
            "README.md": page("skills/ux-design/SKILL.md", "agents/ux-reviewer.md"),
        }), [])

    def test_passes_a_row_that_links_an_anchor(self):
        self.assertEqual(self.check({
            "skills/ux-design/SKILL.md": "x",
            "README.md": page("skills/ux-design/SKILL.md#project-config"),
        }), [])

    def test_flags_a_skill_with_no_row(self):
        self.assertEqual(self.check({
            "skills/ux-design/SKILL.md": "x",
            "agents/ux-reviewer.md": "x",
            "README.md": page("agents/ux-reviewer.md"),
        }), ["plugins/giga-ux/README.md: no row for giga-ux:ux-design"])

    def test_flags_an_agent_with_no_row(self):
        self.assertEqual(self.check({
            "skills/ux-design/SKILL.md": "x",
            "agents/ux-reviewer.md": "x",
            "README.md": page("skills/ux-design/SKILL.md"),
        }), ["plugins/giga-ux/README.md: no row for giga-ux:ux-reviewer"])

    def test_flags_a_skill_linked_only_in_prose(self):
        self.assertEqual(self.check({
            "skills/ux-design/SKILL.md": "x",
            "README.md": "See [its config](skills/ux-design/SKILL.md#project-config).\n" + page(),
        }), ["plugins/giga-ux/README.md: no row for giga-ux:ux-design"])

    def test_flags_every_skill_and_agent_without_a_page(self):
        self.assertEqual(self.check({"skills/ux-design/SKILL.md": "x", "agents/ux-reviewer.md": "x"}), [
            "plugins/giga-ux/README.md: no row for giga-ux:ux-design",
            "plugins/giga-ux/README.md: no row for giga-ux:ux-reviewer",
        ])

    def test_passes_a_plugin_with_no_skills_or_agents(self):
        self.assertEqual(self.check({"hooks/hooks.json": "{}"}), [])

    def test_main_fails_on_a_skill_with_no_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp, "plugins/a/skills/x/SKILL.md"), "Intro.\n")
            write(Path(tmp, "plugins/a/skills/y/SKILL.md"), "Intro.\n")
            write(Path(tmp, "plugins/a/README.md"), page("skills/x/SKILL.md"))
            write(Path(tmp, "README.md"), "Intro.\n")
            err = io.StringIO()
            with mock.patch.object(check, "ROOT", Path(tmp)), contextlib.redirect_stderr(err):
                self.assertEqual(check.main(), 1)
            self.assertEqual(err.getvalue(),
                             "A skill or agent has no row on its plugin's page:\n"
                             "  plugins/a/README.md: no row for a:y\n")


class PublishedTreeTest(unittest.TestCase):
    def test_no_bare_names(self):
        self.assertEqual(check.published_bare_names(REPO, check.owners(PLUGINS)), [])

    def test_no_leaks(self):
        self.assertEqual(check.published_leaks(REPO, FORBIDDEN), [])

    def test_no_arg_refs(self):
        self.assertEqual(check.arg_refs(PLUGINS, REPO), [])

    def test_every_skill_and_agent_has_a_row(self):
        self.assertEqual([x for p in real_plugins() for x in check.unlisted(p, REPO)], [])


if __name__ == "__main__":
    unittest.main()
