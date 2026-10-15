---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask one question at a time only when an answer gates what to ask next. When questions are independent — no causal or logical dependency between the answers — batch them together, a few at a time (4 max), so we cover parallel branches in one round.

If a question can be answered by exploring the codebase, explore the codebase instead.

If a later answer contradicts an earlier one, surface the contradiction and re-resolve that branch before moving on.

When every branch is resolved, close with a compact summary: the decisions made and any questions deferred.
