# Skills

Personal collection of agent skills for kimi-code and Codex. Skills maintained here are linked into `~/.agents/skills` by `./link.sh`. Runtime companion skills are installed and updated by their upstream tools.

## Index

### `research/` — academic writing & research workflow

- [experiment-lifecycle](research/experiment-lifecycle/SKILL.md) — Plan and analyze experiments around named questions and decisions, using justified priors and purpose-driven designs.
- [figure-designer](research/figure-designer/SKILL.md) — Advises on the three core figures of a technical paper (Motivated Example, Solution Overview, Experimental Results), then runs a quality-control audit.
- [idea-evaluator](research/idea-evaluator/SKILL.md) — Evaluates a preliminary research idea against a five-dimension framework (Higher, Faster, Stronger, Cheaper, Broader) plus a fatal-flaws audit.
- [intro-drafter](research/intro-drafter/SKILL.md) — Drafts a 6-paragraph Introduction outline for a technical paper from a structured flowchart, aligning contributions with challenges.
- [pre-submission-reviewer](research/pre-submission-reviewer/SKILL.md) — Pre-submission review across five dimensions (macro logic, writing, grammar, LaTeX, figures) with a reviewer-style severity taxonomy.
- [research-promotion](research/research-promotion/SKILL.md) — Turn a research contribution's distinctive value into compelling READMEs, model and dataset cards, demos, videos, figures, and social posts.
- [tech-paper-template](research/tech-paper-template/SKILL.md) — Structures a technical paper's full logical skeleton using a thinking-template table, with a four-point self-consistency check.
- [throughput-methodology](research/throughput-methodology/SKILL.md) — Improve training and scientific-computing throughput through measured bottlenecks, targeted interventions, and numerical and semantic validation.
- [vibe-research-workflow](research/vibe-research-workflow/SKILL.md) — Guides AI-assisted research across Vibe Coding, Vibe Figure, and Vibe Writing sub-flows, keeping the user in charge of academic judgment.

### `tools/` — general-purpose utilities

- [archify](tools/archify/SKILL.md) — Create architecture, workflow, sequence, data-flow, and lifecycle diagrams as standalone HTML with SVG; accepts plain language or Mermaid.
- [distill-agent-rule](tools/distill-agent-rule/SKILL.md) — Turn one user complaint about agent behavior into a durable, general rule: interrogate the evidence, formulate the class with its temptation, place it in AGENTS.md, a skill, or a gate.
- [grill-me](tools/grill-me/SKILL.md) — Interview the user relentlessly about a plan or design until reaching shared understanding.
- [mineru](tools/mineru/SKILL.md) — MinerU document parsing API — convert PDF/DOC/PPT/images to Markdown/JSON with OCR, formula recognition, and table extraction.
- [repo-hygiene](tools/repo-hygiene/SKILL.md) — Audience-first doctrine for repository structure and prose, requiring real consumers and useful information.
- [report-writing](tools/report-writing/SKILL.md) — Write analytical reports from available evidence, with targeted research, adaptive presentation, source links, and the requested output format.
- [task-phasing](tools/task-phasing/SKILL.md) — Decompose a large task into an evidence-backed phased roadmap with dependencies, exit criteria, and follow-up prompts.
- [visual-design](tools/visual-design/SKILL.md) — Create presentations and visual assets with separate design workflows, shared editable `.pptd` sources, and validated PPTX export.
- [work-report-writer](tools/work-report-writer/SKILL.md) — Turn work notes and Git history into weekly or monthly reports, with data-oriented, narrative, or OKR-aligned styles.
- [write-a-skill](tools/write-a-skill/SKILL.md) — Create new agent skills with proper structure, progressive disclosure, and bundled resources.

## External runtimes

Run `./update-runtimes.sh all`, or select `lark`, `hf`, or `hyperframes`. The script updates to the latest released runtime, invokes its skill installer, and retains exactly the names in [runtime-skills.json](runtime-skills.json) in `~/.agents/skills`. Upstream skill contents stay unchanged. Unselected skills and agent-specific copies are removed using the upstream `skills` CLI; unrelated skills are preserved.

Requires Python 3.10+, Bash, Git and Node.js 22.20+ with npm/npx. HF also requires [uv](https://docs.astral.sh/uv/getting-started/installation/). Put the npm global bin directory and `uv tool dir --bin` on your `PATH`.

| Tool | Runtime installation/update | Skill installation |
| --- | --- | --- |
| [Lark CLI](https://github.com/larksuite/cli) | Official npm installer on first use; `lark-cli update --force` thereafter | The runtime refreshes its official skill set |
| [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli) | `uv tool install --upgrade huggingface_hub` | `hf skills add <name> --dest ~/.agents/skills --force` |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | `npm install --global hyperframes@latest` | `hyperframes skills` installs the published set before filtering |

Update companion skills through this script. If a task needs an excluded skill, add it to the manifest in a subsequent update. Review companion-skill requirements manually when changing selections. Use `./update-runtimes.sh all --check` to check the installed selections without updating.

HyperFrames setup configures `HYPERFRAMES_SKIP_SKILLS=1` for new Bash, Zsh or Fish sessions to disable automatic additions during normal use. Restart the shell or agent session after setup; for the current shell, run `export HYPERFRAMES_SKIP_SKILLS=1` (Fish: `set -gx HYPERFRAMES_SKIP_SKILLS 1`). The updater explicitly enables skill installation for its own refresh. Other runtime skill-management commands should not be used directly, since they bypass the allowlist.

Unselected skills may briefly exist during an update. Account setup and login remain separate. HyperFrames uses the standalone installation; plugin installations should be managed through their plugin manager. Existing video projects retain their own runtime dependencies.

[Runtime skills CI](.github/workflows/runtime-skills.yml) tests real fresh installations and repeated updates on relevant PRs and pushes to `main`, every Monday, and on manual dispatch. It checks selected names, final installation locations, preservation of unrelated skills, and HyperFrames' automatic-install opt-out. No accounts, training runs, or video renders are required.

## Provenance

- `mineru` — vendored snapshot of the MinerU API skill (cloud API at `mineru.net`); snapshot, check upstream for updates.
- Everything else in `research/` and `tools/` — own.

## Maintenance

- New skill: put it directly under `research/` or `tools/`, add an index line above, run `./link.sh`.
- Retire a skill: `git mv` it to `deprecated/` and run `./link.sh` (prunes the now-broken symlink).
- Update a maintained skill: edit and commit — symlinks make changes live immediately.
- Update external runtimes and their skills: run `./update-runtimes.sh all` or select one tool.
- Link into a different directory: `./link.sh /path/to/skills`. Existing directories and links managed elsewhere are preserved.
