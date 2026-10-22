"""Exercise real upstream installers on a disposable account or CI runner."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", choices=["lark", "hf", "hyperframes"])
    args = parser.parse_args()
    selected = set(json.loads((REPO / "runtime-skills.json").read_text())[args.runtime])
    home = Path.home()
    canonical = home / ".agents/skills"
    canonical.mkdir(parents=True, exist_ok=True)
    if list(canonical.iterdir()):
        raise RuntimeError("Run this integration test on a disposable account with no installed skills.")
    if args.runtime == "hyperframes":
        # Exercise Bash's login-file precedence even on minimal container images.
        (home / ".bash_profile").touch(exist_ok=True)

    # Make upstream exercise copying and mirroring, not just a pristine home.
    other_roots = [home / ".claude/skills", home / ".cursor/skills", home / ".config/opencode/skills"]
    for root in [canonical, *other_roots]:
        fixture = root / "unrelated-skill"
        fixture.mkdir(parents=True)
        (fixture / "SKILL.md").write_text("---\nname: unrelated-skill\ndescription: Local integration fixture.\n---\n")
        (fixture / "data.txt").write_text(str(root))
    preserved = {root: snapshot(root / "unrelated-skill") for root in [canonical, *other_roots]}
    repo_before = run("git", "status", "--porcelain", cwd=REPO, capture_output=True).stdout

    for iteration in range(2):
        run(str(REPO / "update-runtimes.sh"), args.runtime, cwd=REPO)
        run(str(REPO / "update-runtimes.sh"), args.runtime, "--check", cwd=REPO)
        assert {p.name for p in canonical.iterdir() if not p.name.startswith(".")} == selected | {"unrelated-skill"}
        for root in other_roots:
            assert {p.name for p in root.iterdir() if not p.name.startswith(".")} == {"unrelated-skill"}, root
        for root, expected in preserved.items():
            assert snapshot(root / "unrelated-skill") == expected, root

        # The upstream inventory knows additional agent destinations too. With
        # no mirrors, selected skills have the same readers as a universal-only skill.
        (canonical / "universal-only").mkdir()
        (canonical / "universal-only/SKILL.md").write_text("---\nname: universal-only\ndescription: Universal store fixture.\n---\n")
        with tempfile.TemporaryFile(mode="w+") as output:
            run("npx", "--yes", "skills", "list", "--global", "--json", stdout=output)
            output.seek(0)
            entries = json.load(output)
        by_name = {entry["name"]: entry for entry in entries}
        universal_readers = set(by_name["universal-only"]["agents"])
        for name in selected:
            assert set(by_name[name]["agents"]) == universal_readers, by_name[name]
        (canonical / "universal-only/SKILL.md").unlink()
        (canonical / "universal-only").rmdir()

        if args.runtime == "hf" and iteration == 0:
            # An actual unselected marketplace install must disappear on refresh.
            hf = str(Path(run("uv", "tool", "dir", "--bin", capture_output=True).stdout.strip()) / "hf")
            run(hf, "skills", "add", "huggingface-papers", "--global", "--force")

    if args.runtime == "hyperframes":
        before = snapshot(canonical)
        env = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1")
        with tempfile.TemporaryDirectory() as work:
            run("npx", "--yes", "hyperframes", "skills", "update", "figma", env=env, cwd=work)
        assert snapshot(canonical) == before, "HyperFrames added a skill during normal use"
        value = run("bash", "-lc", 'printf "%s" "$HYPERFRAMES_SKIP_SKILLS"', capture_output=True).stdout
        assert value == "1", "New shells do not disable automatic skill installation"

    assert run("git", "status", "--porcelain", cwd=REPO, capture_output=True).stdout == repo_before
    print(f"{args.runtime}: fresh install, repeated update, selection and destination checks passed")


if __name__ == "__main__":
    main()
