---
name: repo-hygiene
description: 'Audience-first doctrine for repository content: structure is kept only for a consumer that exists today, prose is kept only when it changes what its reader may conclude or do — bloat and slop share one root, writing for an imaginary audience. Use when adding or keeping files, configs, fields, mechanisms, or indirection layers; when writing or editing docs, notes, ledgers, reports, error messages, or comments; when reviewing or cleaning existing code and docs; when considering version markers, hashes, receipts, disclaimers, or "just in case" structure.'
---

# Repo hygiene

**Write only for the audience that exists.** The real audience is two: the run that executes the code, and the reader at HEAD trying to understand the system. Every line — structure or prose — has an intended beneficiary, and that beneficiary must exist. The imaginary audience takes many faces: an auditor demanding provenance, a hostile reviewer pouncing on unhedged claims, a careless operator, a future second version, a confused reader needing reassurance, a future self who might need this script. Lines written for any of them are bloat or slop however carefully crafted, and their cost lands on the real reader. Completeness is not a purpose. Absence already communicates absence.

## 1. Never add or keep structure without a consumer that exists today

Every file, config, field, mechanism, and indirection layer must name its consumer: a caller that executes it, a behavior it changes, a decision it feeds. "The parser requires it" is not a consumer — a validator that only checks presence manufactures fields nobody reads. "Just in case", "might be needed later", "for a future version" are not consumers.

- Temptation: each layer is individually cheap and signals diligence — a registry, a handshake, a version marker, a receipt file all look like engineering.
- Positive control: receipts a program writes to itself and then authenticates; version markers where exactly one version ever existed; one value re-validated at five layers; two processes built from the same commit authenticating each other like strangers — all die.
- Overreach: validation at genuine boundaries stays (config parsing, external endpoints, downloaded artifacts); handling for real failure modes stays (timeouts, nonzero exits). The rule kills guards for unreachable states and for hostile callers inside one trust boundary.

## 2. Never pin bytes where semantics is the question

Where a consistency guard does real work, compare parsed semantics, never byte hashes. A hash in a config answers "are these the same bytes as when pinned?" — a question nobody asks — and floods every reader with hex to defend against a swap that has no actor. The semantic comparison is strictly better: it survives comment edits and states what actually must match.

- Temptation: pinning feels free and rigorous — compute the hash, check the hash, catch "tampering" — and a green check reads like safety whatever it guards.
- Positive control: an arm config carrying `{asset, weights}` still evaluates exactly the intended checkpoint, because the asset map is the locator; a resume guard comparing parsed config equality still catches the real hazard — resumed-with-changed-semantics.
- Overreach: internal identity hashing that never appears in any config or readable artifact stays (cache keys, RNG domain separators); verification of downloaded artifacts at provisioning time stays, where the download itself is the risk.

## 3. One-off code is deleted once its evidence is extracted

The note is the archive, and the script is regenerable from it. Kept "just in case", a stale one-off taxes every future reader — its beneficiary is an imagined future self, and that self never comes. This applies to the whole workspace, tracked or not. If a one-off proves repeatedly useful, promote it into a real tool; the forbidden state is kept-but-unpromoted.

- Temptation: the script is the task's visible output, so deleting it feels like destroying work, and "just in case" feels prudent.
- Positive control: before keeping any file, name who will open it again and when. If the answer is "someone, someday, maybe", delete it; the archive already holds what it proved.
- Overreach: promotion is the named exception — a one-off with repeated live use becomes a real tool in its proper location, without its scaffolding.

## 4. The repo is written for a reader who has only HEAD

Never let session context become shared structure: no decision labels made of dates, no citations of discussion rounds, no "the user asked" standing in for a reason — a date may timestamp a record but never names a decision, and attributing a decision to the user is provenance, not rationale. Names are the same surface: a directory or module name must predict its members; organize by what the code does, never by which run, platform, or date produced it. Library locations hold reusable core logic only. Machine-local and credential facts live in untracked local docs, never in tracked files.

- Temptation: the session is your entire context — referencing it costs you nothing and is invisible to you as a defect.
- Positive control: hand the repo to a reader with no session access; every reference resolves, every name predicts its contents, every stated reason is the actual reason.
- Overreach: archived experiment records keep their timestamps and provenance — they are records, not decisions.

## 5. Never write content whose function is to absolve the writer

A sentence, field, label, or comment earns its place by changing what the reader may conclude or do. Performing caution is not conveying information: methodological vocabulary where no method question exists; disclaimers of claims nobody made; confounders, control groups, and limitations enumerated with no decision at stake; events reported "for completeness"; conclusions that restate the premise after six hedges; labels that say what a thing is not.

- Temptation: hedging is always safe and always sounds careful; a disclaimer costs the writer nothing and transfers the cost to every reader.
- Positive control: a hedge earns its sentence only when it negates a conclusion the reader would actually have drawn. "This lunch's price does not extrapolate to other cities, seasons, or inflation environments" negates nothing anyone would conclude; "this reward metric rises on visibly degraded outputs, so it is not an acceptance proxy" negates exactly what a tired reader would assume. Same grammatical form, opposite density.
- Overreach: honest scope statements stay mandatory where a real over-read is live — one precise sentence stating what a signal does and does not prove. The rule kills the apparatus, not the honesty.
