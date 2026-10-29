#!/usr/bin/env python3
"""Check the published tree: no private content, no broken cross-file reads, no bare skill or agent names,
no `$<digit>` in a skill or agent body, and a row on its plugin's page for every skill and agent.

Usage: scripts/check_plugins.py
Rules: README § How this repo is built.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_REF = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/\.\./([\w-]+)/([^\s`'\")\]]+)")
FORBIDDEN = [
    "/Users/",
    "@gigasoftware\\.io",
    "claude\\.ai/(code/)?artifact/",
    "atlassian\\.net",
    "[a-z]+_secrets\\b",
    "github_pat_|ghp_[A-Za-z0-9]|ATATT",
]
PUBLISHED = ["plugins", "docs", "README.md"]
ARG = r"\$[0-9]"


def owners(plugins_dir: Path) -> dict[str, str]:
    """Map every skill and agent name to the plugin that ships it."""
    found = {}
    for plugin in sorted(p for p in plugins_dir.iterdir() if p.is_dir()):
        for skill in plugin.glob("skills/*/SKILL.md"):
            found[skill.parent.name] = plugin.name
        for agent in plugin.glob("agents/*.md"):
            found[agent.stem] = plugin.name
    return found


def namespace(text: str, owner: dict[str, str]) -> str:
    for name in sorted(owner, key=len, reverse=True):
        full = f"{owner[name]}:{name}"
        text = re.sub(rf"`{re.escape(name)}`", f"`{full}`", text)
        # A path segment (`skills/jira`) or a URL is never an invocation.
        text = re.sub(rf"(?<![\w.~/:-])/{re.escape(name)}(?![\w:-])", f"/{full}", text)
    return text


def namespace_preloads(text: str, owner: dict[str, str]) -> str:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return text
    front = match.group(1)
    for name, plugin in owner.items():
        front = re.sub(rf"^(\s+-\s+){re.escape(name)}\s*$", rf"\g<1>{plugin}:{name}", front, flags=re.M)
    return f"---\n{front}\n---\n" + text[match.end():]


def leaks(tree: Path, patterns: list[str], base: Path | None = None) -> list[str]:
    """List each line under tree that matches a pattern, by its path from base (default: the tree, or a file's dir)."""
    base = base or (tree.parent if tree.is_file() else tree)
    found = []
    files = [tree] if tree.is_file() else sorted(p for p in tree.rglob("*") if p.is_file())
    for path in files:
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    found.append(f"{path.relative_to(base)}:{n}: matches {pattern!r}")
    return found


def published_leaks(root: Path, patterns: list[str]) -> list[str]:
    """List the leaks in every published path under root that exists, by its path from root."""
    return [x for rel in PUBLISHED if (root / rel).exists() for x in leaks(root / rel, patterns, root)]


def broken_refs(plugin_dir: Path) -> list[str]:
    """List each `${CLAUDE_SKILL_DIR}/../<skill>/<file>` that does not resolve inside the plugin."""
    found = []
    for path in sorted(p for p in plugin_dir.rglob("*") if p.is_file()):
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for match in SKILL_REF.finditer(line):
                skill, rel = match.group(1), match.group(2).rstrip(".,;:")
                if not (plugin_dir / "skills" / skill / rel).exists():
                    where = path.relative_to(plugin_dir.parent)
                    found.append(f"{where}:{n}: {skill}/{rel} is not in {plugin_dir.name}")
    return found


def bare_names(tree: Path, owner: dict[str, str], base: Path | None = None) -> list[str]:
    """List each line under tree that names a skill or agent without its plugin prefix, by its path from base (default: the tree's parent)."""
    base = base or tree.parent
    found = []
    for path in [tree] if tree.is_file() else sorted(tree.rglob("*.md")):
        text = path.read_text(errors="replace")
        where = path.relative_to(base)
        for n, line in enumerate(text.splitlines(), 1):
            if namespace(line, owner) == line:
                continue
            for name in owner:
                if namespace(line, {name: owner[name]}) != line:
                    found.append(f"{where}:{n}: bare {name}")
        if path.parent.name == "agents" and namespace_preloads(text, owner) != text:
            found.append(f"{where}:1: bare preloaded skill in front matter")
    return found


def published_bare_names(root: Path, owner: dict[str, str]) -> list[str]:
    """List the bare names in every published path under root that exists, by its path from root."""
    return [x for rel in PUBLISHED if (root / rel).exists() for x in bare_names(root / rel, owner, root)]


def arg_refs(plugins_dir: Path, base: Path) -> list[str]:
    """List each `$<digit>` in a SKILL.md or agent body, by its path from base: Claude Code replaces it with an argument."""
    bodies = sorted([*plugins_dir.glob("*/skills/*/SKILL.md"), *plugins_dir.glob("*/agents/*.md")])
    return [x for path in bodies for x in leaks(path, [ARG], base)]


def unlisted(plugin_dir: Path, base: Path | None = None) -> list[str]:
    """List each skill and agent that no table row of its plugin's README.md links, by the page's path from base (default: the plugins dir)."""
    base = base or plugin_dir.parent
    page = plugin_dir / "README.md"
    lines = page.read_text(errors="replace").splitlines() if page.exists() else []
    rows = [line for line in lines if line.lstrip().startswith("|")]
    targets = [(p.parent.name, f"skills/{p.parent.name}/SKILL.md") for p in sorted(plugin_dir.glob("skills/*/SKILL.md"))]
    targets += [(p.stem, f"agents/{p.name}") for p in sorted(plugin_dir.glob("agents/*.md"))]
    found = []
    for name, target in targets:
        link = re.compile(rf"\]\({re.escape(target)}(#[^)]*)?\)")
        if not any(link.search(row) for row in rows):
            found.append(f"{page.relative_to(base)}: no row for {plugin_dir.name}:{name}")
    return found


def report(heading: str, problems: list[str]) -> None:
    print(f"{heading}:", file=sys.stderr)
    print("\n".join(f"  {p}" for p in problems), file=sys.stderr)


def main() -> int:
    plugins_dir = ROOT / "plugins"
    plugins = sorted(p for p in plugins_dir.iterdir() if p.is_dir())
    owner = owners(plugins_dir)

    leaked = published_leaks(ROOT, FORBIDDEN)
    broken = {p.name: broken_refs(p) for p in plugins}
    bare = published_bare_names(ROOT, owner)
    args = arg_refs(plugins_dir, ROOT)
    rowless = [x for p in plugins for x in unlisted(p, ROOT)]

    failed = False
    for heading, problems in (
        ("Private content", leaked),
        ("A skill reads a file outside its plugin", [x for v in broken.values() for x in v]),
        ("A skill or agent is named without its plugin prefix", bare),
        ("A skill or agent body holds `$<digit>`, which Claude Code replaces with an argument", args),
        ("A skill or agent has no row on its plugin's page", rowless),
    ):
        if problems:
            report(heading, problems)
            failed = True
    if failed:
        return 1

    for plugin in plugins:
        skills = len(list(plugin.glob("skills/*/SKILL.md")))
        agents = len(list(plugin.glob("agents/*.md")))
        print(f"ok {plugin.name}: {skills} skills, {agents} agents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
