#!/usr/bin/env python3
"""Refresh upstream skills, then keep the selected skills in the universal store."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "runtime-skills.json"
SOURCES = {
    "lark": {"larksuite/cli", "open.feishu.cn", "open.larksuite.com"},
    "hf": {"huggingface/skills"},
    "hyperframes": {"heygen-com/hyperframes"},
}


def load_manifest(path=MANIFEST):
    manifest = json.loads(path.read_text())
    if set(manifest) != set(SOURCES):
        raise ValueError("The manifest must contain lark, hf and hyperframes.")
    for runtime, names in manifest.items():
        if not isinstance(names, list) or not names:
            raise ValueError(f"{runtime}: expected a nonempty list of skill names")
        if any(not isinstance(n, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", n) for n in names):
            raise ValueError(f"{runtime}: invalid skill name")
        if len(names) != len(set(names)):
            raise ValueError(f"{runtime}: duplicate skill name")
    return manifest


def run(*args, capture=False, **kwargs):
    if not capture:
        subprocess.run(args, check=True, **kwargs)
        return None
    # Some Node CLIs exit before a piped stdout is flushed. A regular file
    # captures their complete JSON, including inventories larger than 8 KiB.
    with tempfile.TemporaryFile(mode="w+") as output:
        subprocess.run(args, check=True, stdout=output, **kwargs)
        output.seek(0)
        return output.read().strip()


def inventory():
    return json.loads(run("npx", "--yes", "skills", "list", "--global", "--json", capture=True))


def owned_skills(runtime, entries):
    return {
        entry["name"] for entry in entries
        if entry.get("source") in SOURCES[runtime]
        or (runtime == "hf" and (Path(entry["path"]) / ".hf-skill-manifest.json").is_file())
    }


def validate_installed(names, destination):
    for name in names:
        path = destination / name / "SKILL.md"
        if not path.is_file():
            raise RuntimeError(f"Selected skill was not installed: {name}")
        text = path.read_text()
        frontmatter = text.split("---", 2)
        if len(frontmatter) != 3:
            raise RuntimeError(f"Missing skill frontmatter: {path}")
        match = re.search(r"^name:\s*([^\n]+)", frontmatter[1], re.MULTILINE)
        if not match or match[1].strip().strip("\"'") != name:
            raise RuntimeError(f"Installed skill name does not match {name}: {path}")


def reconcile(runtime, selected, home, *, workdir):
    destination = home / ".agents/skills"
    entries = inventory()
    owned = owned_skills(runtime, entries)
    missing = set(selected) - owned
    if missing:
        raise RuntimeError(f"{runtime}: upstream did not install selected skills: {', '.join(sorted(missing))}")
    validate_installed(selected, destination)

    lock_path = home / ".agents/.skill-lock.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {"skills": {}}
    kept_entries = {name: lock["skills"][name] for name in selected if name in lock["skills"]}

    # Upstream knows all agent destinations. Keep the selected bytes while it
    # removes the runtime's installations and mirrors, then restore one copy.
    with tempfile.TemporaryDirectory(prefix="selected-skills-") as temp:
        backup = Path(temp)
        for name in selected:
            shutil.copytree(destination / name, backup / name)
        try:
            run("npx", "--yes", "skills", "remove", *sorted(owned), "--global", "--yes", cwd=workdir)
        finally:
            destination.mkdir(parents=True, exist_ok=True)
            for name in selected:
                target = destination / name
                if target.is_symlink():
                    target.unlink()
                elif target.exists():
                    shutil.rmtree(target)
                shutil.copytree(backup / name, target)
            if kept_entries:
                lock = json.loads(lock_path.read_text())
                lock["skills"].update(kept_entries)
                lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    check(runtime, selected, home)


def check(runtime, selected, home):
    actual = owned_skills(runtime, inventory())
    if actual != set(selected):
        raise RuntimeError(f"{runtime}: installed {sorted(actual)}, expected {sorted(selected)}")
    validate_installed(selected, home / ".agents/skills")
    print(f"{runtime}: {len(selected)} selected skills installed in ~/.agents/skills", flush=True)


def detach_legacy_links(runtime, home):
    source = {"lark": REPO / "lark", "hf": REPO / "tools/hf-cli"}.get(runtime)
    if source is None:
        return
    roots = [home / ".agents/skills", Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")) / "skills",
             Path(os.environ.get("CODEX_HOME", home / ".codex")) / "skills"]
    for root in roots:
        for link in root.glob("*"):
            if link.is_symlink() and link.resolve().is_relative_to(source):
                link.unlink()


def enable_managed_skills(home):
    """Disable HyperFrames' automatic skill writes in future shell sessions."""
    shell = Path(os.environ.get("SHELL", "/bin/bash")).name
    if shell == "fish":
        config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        path = config / "fish/conf.d/runtime-skills.fish"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Companion skills are managed by update-runtimes.sh.\nset -gx HYPERFRAMES_SKIP_SKILLS 1\n")
    else:
        line = "export HYPERFRAMES_SKIP_SKILLS=1 # Companion skills are managed by update-runtimes.sh."
        paths = [Path(os.environ.get("ZDOTDIR", home)) / ".zshenv"] if shell == "zsh" else [home / ".profile", home / ".bashrc"]
        for path in paths:
            text = path.read_text() if path.exists() else ""
            if line not in text.splitlines():
                with path.open("a") as stream:
                    stream.write("\n" + line + "\n")


def install(runtime, selected, home):
    detach_legacy_links(runtime, home)
    # A neutral working directory avoids project-local installer discovery.
    with tempfile.TemporaryDirectory(prefix="runtime-skills-") as temp:
        print(f"Updating {runtime} and its skills...", flush=True)
        if runtime == "lark":
            if shutil.which("lark-cli"):
                run("lark-cli", "update", "--force", cwd=temp)
            else:
                run("npx", "--yes", "@larksuite/cli@latest", "install", stdin=subprocess.DEVNULL, cwd=temp)
        elif runtime == "hf":
            run("uv", "tool", "install", "--upgrade", "huggingface_hub", cwd=temp)
            hf = str(Path(run("uv", "tool", "dir", "--bin", capture=True)) / "hf")
            available = {entry["name"] for entry in json.loads(run(hf, "skills", "list", "--json", capture=True, cwd=temp))}
            missing = set(selected) - available
            if missing:
                raise RuntimeError(f"Unknown Hugging Face skills: {', '.join(sorted(missing))}")
            for name in selected:
                run(hf, "skills", "add", name, "--dest", str(home / ".agents/skills"), "--force", cwd=temp)
        else:
            run("npm", "install", "--global", "hyperframes@latest", cwd=temp)
            binary = str(Path(run("npm", "prefix", "--global", capture=True)) / "bin/hyperframes")
            env = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="0")
            run(binary, "skills", cwd=temp, env=env)
        reconcile(runtime, selected, home, workdir=temp)
        if runtime == "hyperframes":
            enable_managed_skills(home)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", choices=[*SOURCES, "all"])
    parser.add_argument("--check", action="store_true", help="Verify installed selections without updating")
    args = parser.parse_args()
    manifest = load_manifest()
    runtimes = list(manifest) if args.runtime == "all" else [args.runtime]
    for runtime in runtimes:
        if args.check:
            check(runtime, manifest[runtime], Path.home())
        else:
            install(runtime, manifest[runtime], Path.home())


if __name__ == "__main__":
    main()
