# Skills

Personal collection of agent skills for kimi-code and Codex. This repo is the source of truth; the harnesses see them as symlinks in `~/.agents/skills`, created by running `./link.sh`.

## Index

### `lark/` — 飞书/Lark via lark-cli

- [lark-approval](lark/lark-approval/SKILL.md) — 飞书审批：查询和处理审批待办/已办/实例，搜索可发起审批定义并发起原生审批实例。
- [lark-apps](lark/lark-apps/SKILL.md) — 妙搭（Spark/Miaoda）应用开发与托管：应用创建、本地全栈开发、云端生成迭代、创意设计。
- [lark-base](lark/lark-base/SKILL.md) — 飞书多维表格（Base）操作：建表、字段、记录、视图、统计、公式/lookup、表单、仪表盘。
- [lark-calendar](lark/lark-calendar/SKILL.md) — 飞书日历：管理日历日程和会议室。查看/搜索日程、创建/更新日程、查询忙闲、预定会议室。
- [lark-doc](lark/lark-doc/SKILL.md) — 飞书云文档（Docx / Wiki）内容操作：读取、创建、编辑文档，插入或下载图片附件，操作思维笔记。
- [lark-drive](lark/lark-drive/SKILL.md) — 飞书云空间（云盘/云存储）：管理 Drive 文件和文件夹，上传/下载、权限、版本和本地文件导入。
- [lark-event](lark/lark-event/SKILL.md) — Lark/Feishu real-time event listening: stream events as NDJSON via `lark-cli event consume`, for bots and long-running subscribers.
- [lark-im](lark/lark-im/SKILL.md) — 飞书即时通讯：收发消息和管理群聊，搜索聊天记录，上传下载图片和文件，处理交互卡片。
- [lark-markdown](lark/lark-markdown/SKILL.md) — 飞书 Markdown：查看、创建、上传、编辑和比较飞书中的原生 Markdown 文件。
- [lark-note](lark/lark-note/SKILL.md) — 仅当用户或上游配置显式指定 lark-note 时使用，相关请求统一交由 lark-meeting 技能处理。
- [lark-openapi-explorer](lark/lark-openapi-explorer/SKILL.md) — 飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。
- [lark-shared](lark/lark-shared/SKILL.md) — lark-cli setup/auth tasks: auth login/status/logout, user vs bot identity, permissions, missing scopes.
- [lark-slides](lark/lark-slides/SKILL.md) — 飞书幻灯片：创建和编辑幻灯片，读取幻灯片内容，管理幻灯片页面。
- [lark-task](lark/lark-task/SKILL.md) — 飞书任务：管理任务、清单和任务智能体。创建待办、更新状态、拆分子任务、分配协作成员。
- [lark-wiki](lark/lark-wiki/SKILL.md) — 飞书知识库：管理知识空间、空间成员和文档节点。

### `research/` — academic writing & research workflow

- [benchmark-paper-template](research/benchmark-paper-template/SKILL.md) — Structures benchmark/evaluation papers using the five-pillar framework; returns a completeness audit, Introduction logic chain, skeleton, and checklist.
- [figure-designer](research/figure-designer/SKILL.md) — Advises on the three core figures of a technical paper (Motivated Example, Solution Overview, Experimental Results), then runs a quality-control audit.
- [idea-evaluator](research/idea-evaluator/SKILL.md) — Evaluates a preliminary research idea against a five-dimension framework (Higher, Faster, Stronger, Cheaper, Broader) plus a fatal-flaws audit.
- [intro-drafter](research/intro-drafter/SKILL.md) — Drafts a 6-paragraph Introduction outline for a technical paper from a structured flowchart, aligning contributions with challenges.
- [pre-submission-reviewer](research/pre-submission-reviewer/SKILL.md) — Pre-submission review across five dimensions (macro logic, writing, grammar, LaTeX, figures) with a reviewer-style severity taxonomy.
- [tech-paper-template](research/tech-paper-template/SKILL.md) — Structures a technical paper's full logical skeleton using a thinking-template table, with a four-point self-consistency check.
- [vibe-research-workflow](research/vibe-research-workflow/SKILL.md) — Guides AI-assisted research across Vibe Coding, Vibe Figure, and Vibe Writing sub-flows, keeping the user in charge of academic judgment.

### `tools/` — general-purpose utilities

- [archify](tools/archify/SKILL.md) — Create architecture, workflow, sequence, data-flow, and lifecycle diagrams as standalone HTML with SVG; accepts plain language or Mermaid.
- [grill-me](tools/grill-me/SKILL.md) — Interview the user relentlessly about a plan or design until reaching shared understanding.
- [hf-cli](tools/hf-cli/SKILL.md) — Hugging Face Hub CLI (`hf`) for downloading, uploading, and managing models, datasets, spaces, jobs, papers, and more.
- [mineru](tools/mineru/SKILL.md) — MinerU document parsing API — convert PDF/DOC/PPT/images to Markdown/JSON with OCR, formula recognition, and table extraction.
- [orchestration](tools/orchestration/SKILL.md) — Orca orchestration for structured multi-agent coordination: threaded messages, blocking ask/reply flows, task DAGs, decision gates.
- [task-phasing](tools/task-phasing/SKILL.md) — Decompose a large task into an evidence-backed phased roadmap with dependencies, exit criteria, and follow-up prompts.
- [write-a-skill](tools/write-a-skill/SKILL.md) — Create new agent skills with proper structure, progressive disclosure, and bundled resources.

## Provenance

- `lark-*` (15 skills) — vendored snapshot of the lark-cli skill set (each declares `requires.bins: ["lark-cli"]`); snapshot, check upstream for updates.
- `hf-cli` — vendored snapshot from Hugging Face (ships `.hf-skill-manifest.json`, installed revision `890d43c`); snapshot, check upstream for updates.
- `mineru` — vendored snapshot of the MinerU API skill (cloud API at `mineru.net`); snapshot, check upstream for updates.
- Everything in `research/` and the rest of `tools/` — own.

## Maintenance

- New skill: put it in a bucket, add an index line above, run `./link.sh`.
- Retire a skill: `git mv` it to `deprecated/` and run `./link.sh` (prunes the now-broken symlink).
- Update a skill: edit and commit — symlinks make changes live immediately.
