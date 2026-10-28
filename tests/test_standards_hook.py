import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "plugins/giga-standards/hooks/inject-standards.sh"
SENTENCE = "Prefer signals over subjects in every component."
PATTERN_ID = "no-any-type"
BUDGET = 9800


def clean_env(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(extra)
    return env


def git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=clean_env())


@unittest.skipUnless(shutil.which("jq") and shutil.which("git"), "needs jq and git")
class InjectStandardsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git_init(self.repo)
        self.write("docs/constraints.md", f"# Constraints\n\n## Conventions\n\n{SENTENCE}\n\n## Other\n\nUnrelated.\n")
        self.write("docs/anti-patterns.json", json.dumps({"patterns": [
            {"id": PATTERN_ID, "severity": "blocker", "description": "Do not use any.", "fix": "Type it."},
        ]}))
        self.write(".claude/giga/config.json", json.dumps({"standards": {
            "constraintsFile": "docs/constraints.md",
            "antiPatternsFile": "docs/anti-patterns.json",
            "budgetBytes": BUDGET,
            "artifacts": [{"match": ["*.ts"], "artifact": "source",
                           "sections": ["Conventions"], "antiPatterns": [PATTERN_ID]}],
        }}))
        self.session = f"test-{uuid.uuid4().hex}"
        self.markers = self.tmp / "markers"
        self.markers.mkdir()

    def write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_hook(self) -> subprocess.CompletedProcess:
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(self.repo / "src/a.ts")},
            "session_id": self.session,
            "cwd": str(self.repo),
        }
        env = clean_env(TMPDIR=str(self.markers))
        return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), capture_output=True,
                              text=True, env=env, check=False)

    def test_injects_the_routed_standards_within_budget(self):
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(SENTENCE, context)
        self.assertIn("[blocker] Do not use any. → Type it.", context)
        self.assertLessEqual(len(context.encode("utf-8")), BUDGET)

    def test_a_second_write_in_the_same_session_injects_nothing(self):
        self.run_hook()
        again = self.run_hook()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(again.stdout.strip(), "")

    def test_inherited_git_env_cannot_redirect_the_fixture_repo(self):
        outer = self.tmp / "outer"
        outer.mkdir()
        git_init(outer)
        inner = self.tmp / "inner"
        inner.mkdir()
        with mock.patch.dict(os.environ, {"GIT_DIR": str(outer / ".git")}):
            git_init(inner)
        bare = subprocess.run(["git", "config", "--get", "core.bare"], cwd=outer, check=True,
                              capture_output=True, text=True, env=clean_env())
        self.assertEqual(bare.stdout.strip(), "false")
        self.assertTrue((inner / ".git").is_dir())


if __name__ == "__main__":
    unittest.main()
