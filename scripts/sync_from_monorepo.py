#!/usr/bin/env python3
"""Publish skills and agents from the source monorepo into this marketplace's plugins.

Usage: scripts/sync_from_monorepo.py [--source PATH] [--dry-run]
The namespacing, leak and cross-plugin rules: README § How this repo is built.
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_REF = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/\.\./([\w-]+)/([^\s`'\")\]]+)")


def owners(plugins: dict) -> dict[str, str]:
    """Map every skill and agent name to the plugin that ships it."""
    return {name: plugin for plugin, spec in plugins.items()
            for name in spec.get("skills", []) + spec.get("agents", [])}


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


def build_plugin(src: Path, out: Path, spec: dict, owner: dict[str, str]) -> None:
    for skill in spec.get("skills", []):
        shutil.copytree(src / ".claude" / "skills" / skill, out / "skills" / skill)
    agents = spec.get("agents", [])
    if agents:
        (out / "agents").mkdir(parents=True, exist_ok=True)
    for agent in agents:
        shutil.copy2(src / ".claude" / "agents" / f"{agent}.md", out / "agents" / f"{agent}.md")
    for md in out.rglob("*.md"):
        text = namespace(md.read_text(), owner)
        if md.parent.name == "agents":
            text = namespace_preloads(text, owner)
        md.write_text(text)


def leaks(tree: Path, patterns: list[str]) -> list[str]:
    found = []
    for path in sorted(p for p in tree.rglob("*") if p.is_file()):
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    found.append(f"{path.relative_to(tree)}:{n}: matches {pattern!r}")
    return found


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

    owner = owners(config["plugins"])
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp)
        for plugin, spec in config["plugins"].items():
            build_plugin(src, staged / plugin, spec, owner)

        problems = leaks(staged, config.get("forbidden", []))
        if problems:
            print("Refusing to publish — private content in the copied files:", file=sys.stderr)
            print("\n".join(f"  {p}" for p in problems), file=sys.stderr)
            return 1

        broken = [ref for plugin in config["plugins"] for ref in broken_refs(staged / plugin)]
        if broken:
            print("Refusing to publish — a skill reads a file outside its plugin:", file=sys.stderr)
            print("\n".join(f"  {b}" for b in broken), file=sys.stderr)
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
