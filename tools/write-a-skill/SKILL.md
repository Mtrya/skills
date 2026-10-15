---
name: write-a-skill
description: Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new skill, or turn a workflow from the current session into a reusable skill.
---

# Writing Skills

## Process

1. **Capture intent** - if the conversation already contains the workflow to capture ("turn this into a skill"), mine the history first: tools used, sequence of steps, corrections the user made, input/output formats. Then ask the user to fill gaps:
   - What task/domain does the skill cover?
   - What specific use cases should it handle?
   - When should it trigger (phrases, contexts, file types)?
   - Does it need executable scripts or just instructions?
   - Any reference materials to include?

2. **Draft in the conversation** - output the proposed SKILL.md (and any bundled files) as your reply, not as files on disk. The user reviews the draft: does it cover the use cases, anything missing or unclear, any section over- or under-detailed? Iterate until approved.

3. **Write on approval** - only after the user approves, write the files to disk and register the skill (see Registering in a Skills Repo).

## Make It Standalone

A skill must work in a fresh session with zero memory of the conversation that produced it. Session residue is the main failure mode: paths, filenames, project names, and decisions that were true "when we just did it" will be wrong next month in a different project.

When capturing a workflow from conversation history:

- Distill the general procedure; parameterize the specifics (paths, names, URLs become inputs or placeholders, not constants).
- Inline any context the workflow depends on. If a step only makes sense given something the user said in passing, that something belongs in the skill — or the step is wrong.
- Check the draft as a context-free reader would: anything such a reader gets wrong is context the skill failed to carry.

## Skill Structure

```
skill-name/
├── SKILL.md           # Main instructions (required)
├── references/        # Detailed docs loaded on demand (if needed)
│   └── EXAMPLES.md
├── scripts/           # Utility scripts (if needed)
│   └── helper.js
└── assets/            # Templates, fonts, etc. used in output (if needed)
```

The `name` in frontmatter must match the directory name: lowercase letters, digits, hyphens.

## SKILL.md Template

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
---

# Skill Name

## Quick start

[Minimal working example]

## Workflows

[Step-by-step processes with checklists for complex tasks]

## Advanced features

[Link to separate files with when-to-read guidance: See [references/EXAMPLES.md](references/EXAMPLES.md) for ...]
```

Harnesses may support optional frontmatter beyond `name`/`description` (e.g. `requires.bins` to declare required binaries); check what your harness supports.

## Description Requirements

The description is **the only thing your agent sees** when deciding which skill to load. It's surfaced in the system prompt alongside all other installed skills. Your agent reads these descriptions and picks the relevant skill based on the user's request.

**Goal**: Give your agent just enough info to know:

1. What capability this skill provides
2. When/why to trigger it (specific keywords, contexts, file types)

**Format**:

- Max 1024 chars
- Write in third person
- First sentence: what it does
- Second sentence: "Use when [specific triggers]"

All "when to use" information belongs here, not in the body — the body is only read after triggering. Err slightly pushy with triggers; agents under-trigger skills far more often than they over-trigger.

**Good example**:

```
Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when user mentions PDFs, forms, or document extraction.
```

**Bad example**:

```
Helps with documents.
```

The bad example gives your agent no way to distinguish this from other document skills.

## Writing Style

- Imperative form ("Extract the text", not "You should extract the text").
- Explain why a step matters instead of stacking ALL-CAPS MUSTs — agents follow reasoning better than rules.
- Write for the general case, not just the example at hand; the skill will face inputs you didn't see.
- Don't document what the model already knows (how to read a file, what Markdown is); every line costs context on every trigger.

## When to Add Scripts

Add utility scripts when:

- Operation is deterministic (validation, formatting)
- Same code would be generated repeatedly
- Errors need explicit handling

Scripts save tokens and improve reliability vs generated code. State whether the agent should execute a script or read it as reference material.

## When to Split Files

Skills load in three levels: frontmatter metadata (always in context), SKILL.md body (loaded on trigger), bundled resources (loaded on demand). Keep SKILL.md under ~500 lines; split into `references/` when:

- Approaching that limit
- Content has distinct domains (finance vs sales schemas) — one file per variant, so the agent reads only the relevant one
- Advanced features are rarely needed

Reference files over ~300 lines should include a table of contents.

## Registering in a Skills Repo

If the skill lives in a versioned skills repo: put it in the right bucket directory, add an index line to the repo README, and run the repo's link/install script so the harness sees it.

## Review Checklist

After drafting, verify:

- [ ] Description includes triggers ("Use when...") and stays under 1024 chars
- [ ] `name` matches the directory name (lowercase, hyphens)
- [ ] SKILL.md under ~500 lines; larger content split into `references/`
- [ ] Standalone: no reliance on session history; specifics parameterized
- [ ] No time-sensitive info
- [ ] Consistent terminology
- [ ] Concrete examples included
- [ ] References one level deep, each linked with when-to-read guidance
