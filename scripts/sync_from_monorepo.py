#!/usr/bin/env python3
"""Publish skills and agents from the source monorepo into this marketplace's plugins.

The monorepo's `.claude/` is the source of truth; this script copies the skills and agents
named in `sync.json` verbatim, then makes two mechanical changes:

- Plugin components are namespaced (`giga-ux:ux-architect`), so every backticked mention of a
  skill or agent the plugin ships, and every `skills:` preload in an agent's frontmatter, gets
  the plugin prefix.
- Nothing is written if any copied file matches a `forbidden` pattern: this repo is public.

Usage: scripts/sync_from_monorepo.py [--source PATH] [--dry-run]
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def namespace(text: str, plugin: str, names: list[str]) -> str:
    for name in names:
        text = re.sub(rf"`{re.escape(name)}`", f"`{plugin}:{name}`", text)
    return text


def namespace_preloads(text: str, plugin: str, skills: list[str]) -> str:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return text
    front = match.group(1)
    for skill in skills:
        front = re.sub(rf"^(\s+-\s+){re.escape(skill)}\s*$", rf"\g<1>{plugin}:{skill}", front, flags=re.M)
    return f"---\n{front}\n---\n" + text[match.end():]


def build_plugin(src: Path, out: Path, plugin: str, spec: dict) -> None:
    skills, agents = spec.get("skills", []), spec.get("agents", [])
    names = skills + agents
    for skill in skills:
        shutil.copytree(src / ".claude" / "skills" / skill, out / "skills" / skill)
    (out / "agents").mkdir(parents=True, exist_ok=True)
    for agent in agents:
        shutil.copy2(src / ".claude" / "agents" / f"{agent}.md", out / "agents" / f"{agent}.md")
    for md in out.rglob("*.md"):
        text = namespace(md.read_text(), plugin, names)
        if md.parent.name == "agents":
            text = namespace_preloads(text, plugin, skills)
        md.write_text(text)


def leaks(tree: Path, patterns: list[str]) -> list[str]:
    found = []
    for path in sorted(p for p in tree.rglob("*") if p.is_file()):
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    found.append(f"{path.relative_to(tree)}:{n}: matches {pattern!r}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", help="monorepo root (default: sync.json `source`)")
    parser.add_argument("--dry-run", action="store_true", help="build and check, write nothing")
    args = parser.parse_args()

    config = json.loads((ROOT / "sync.json").read_text())
    src = Path(args.source or config["source"]).expanduser()
    if not (src / ".claude").is_dir():
        print(f"no .claude/ under {src}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp)
        for plugin, spec in config["plugins"].items():
            build_plugin(src, staged / plugin, plugin, spec)

        problems = leaks(staged, config.get("forbidden", []))
        if problems:
            print("Refusing to publish — private content in the copied files:", file=sys.stderr)
            print("\n".join(f"  {p}" for p in problems), file=sys.stderr)
            return 1

        for plugin in config["plugins"]:
            dest = ROOT / "plugins" / plugin
            for part in ("skills", "agents"):
                if args.dry_run:
                    continue
                shutil.rmtree(dest / part, ignore_errors=True)
                if (staged / plugin / part).exists():
                    shutil.copytree(staged / plugin / part, dest / part)
            print(f"{'checked' if args.dry_run else 'synced'} {plugin}: "
                  f"{len(config['plugins'][plugin].get('skills', []))} skills, "
                  f"{len(config['plugins'][plugin].get('agents', []))} agents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
