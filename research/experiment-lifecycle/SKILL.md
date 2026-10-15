---
name: experiment-lifecycle
description: Purpose-driven experiment doctrine — fund, design, and analyze training/evaluation runs only against a named question or a needed recipe value, never for completeness. Use when planning experiment campaigns, deciding which arms to fund or skip, sizing sweeps or grids, citing literature priors to justify or refuse a run, or interpreting run results and internal metrics.
---

# Experiment lifecycle

**Experiments are purpose-driven.** Every run exists to answer a named question or to fit a value the final recipe needs — never for completeness, coverage, or curiosity unattached to a decision. Before launch, every arm has written down its purpose and the decision its outcome changes. A run that ends having served no purpose — no question answered, no value fitted — is a failed run, however cleanly it executed. A null that eliminates a named hypothesis has served its purpose; a shrug has not.

## 1. Never fund an arm that cannot name its purpose and its decision

"Cover the space", "ablate everything", "see what happens" are not purposes. If no decision changes with the outcome, the arm is unfundable, and its budget belongs to an arm that moves one.

- Temptation: listing toggles and filling a grid is easier than reasoning about what we want to understand — a full combination table looks like thoroughness.
- Positive control: ask of every proposed arm, "which decision flips if this arm comes out the other way?" Designs assembled by enumerating switch combinations always contain cells that serve no decision; this rule deletes them.
- Overreach: path-qualification runs (does the pipeline execute end-to-end) stay legitimate; their purpose is qualification and they are labeled as such, never presented as evidence.

## 2. Never cite a prior that is not pinned for our setting to skip a run — and never re-run what a pinned prior settles

A prior is pinned when the reference establishes portability (same algorithm family and stack, ablated there) or states a transfer condition we can verify without training. It is open when the reference itself says "tune this", when our stack differs materially, or when no reference exists. Open questions and open parameters get funded runs — sized to fit, predeclared — and an invented constant is never a substitute for a fitted one.

- Temptation: skipping arms wears the costume of rigor — every citation and every saved run reads as discipline, so "insight per experiment" decays into "minimize experiments".
- Positive control: a reference ships a value for its own model while its text says "tune this to your model and data" — that value is exemplified, not pinned, and "the paper used it" is not a reason to skip fitting it here.
- Overreach: genuinely pinned priors (a reference value carrying a verifiable transfer condition) still substitute for runs; the rule never forces re-establishing what is established.

## 3. Never let the design default to whatever shape is at hand — derive it from the purpose

The cheapest design that serves the purpose, and no cheaper: a mechanism question gets a single-axis change against a frozen baseline, with internal-metric trajectories as the primary readout; an open value gets a sweep sized to fit it, with predeclared points, fit form, and selection criterion; interactions get a grid, and only when interactions are the live question. A design too weak to decide is not savings — it is a shrug scheduled in advance.

- Temptation: the grid template and the two-point A/B template are always within reach, while deriving the design from the purpose takes reasoning.
- Positive control: "the minimum setting at which internal metrics stay stable" cannot be decided by comparing two arms' final scores — it needs points spanning the plausible range, read as trajectories. Any proposed design that cannot distinguish the outcomes its purpose cares about fails this rule.
- Overreach: smoke runs stay minimal; the rule governs evidence-producing designs, not pipeline checks.

## 4. Never stop analysis at the headline number — close the loop on the stated purpose

Read full trajectories and internal metrics; state explicitly whether the predeclared hypothesis held. For a value-fit, fit the curve under the predeclared form and criterion and pick the operating point — the best point is never announced as "the winner". Harvest everything the run was built to produce into the next design or the final recipe, naming where each piece landed. If the run cannot serve its purpose, say so: the decision stays open and goes back to the user; a failed arm is never silently rerun or quietly reinterpreted as success.

- Temptation: comparing final numbers is easier than reading curves, and "nothing can be said" is always safe — but an experiment that says nothing produced zero value.
- Positive control: if a run's analysis could have been written without opening the trajectory logs — a final metric, a ranking, a winner — this rule has been violated, whatever the analysis concludes.
- Overreach: interim mechanism-level claims need no held-out confirmation; only winner claims on quality do.
