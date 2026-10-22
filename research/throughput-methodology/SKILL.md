---
name: throughput-methodology
description: Vendor-neutral methodology for improving training or scientific-computing throughput with an agent. Use when the user wants to accelerate training or scientific-computing code, including higher tokens/s, samples/s, simulation or solver throughput, lower time-to-solution, or better utilization and scalability; when deciding among data loading, mixed precision, compiler/runtime, parallel strategy, memory, communication, kernel/operator optimization, or profiler-driven work; when designing repeatable experiments, bottleneck classification, promotion/kill rules, or backend-agnostic optimization plans. Do not use for algorithm research, model architecture redesign, or benchmark claims without measurements.
---

# Throughput Methodology

## Purpose

Guide throughput work as a bounded engineering problem: define the metric, find the binding constraint, choose an intervention by expected benefit and cost, test a focused hypothesis, verify correctness and task-relevant numerical behavior, then promote or kill. Use backend-specific commands only when the backend is known.

## Core Model

Model one iteration as competing resources:

```text
iteration_time ≈ max_{execution paths p} Σ_{i ∈ p} duration_i
throughput ≈ useful_units_per_iteration / iteration_time

iteration_time_lower_bound = max_{resources r}(required_work_r / peak_rate_r)
throughput_ceiling = useful_units_per_iteration / iteration_time_lower_bound
```

Execution paths account for dependencies, resource serialization, and exposed waits. Evaluate resource bounds for the same workload, separately for each device or link: compute operations / compute rate, memory bytes / memory bandwidth, communication bytes / link bandwidth, and input bytes / input bandwidth.

For workloads with overlapping iterations, apply the same formulas to a representative execution window, using the useful work completed within that window.

Useful units can be tokens, samples, grid cells, particles, equations, or optimizer steps. Choose one primary metric and task-relevant guardrails.

## Non-negotiable Rules

- Start from a reproducible baseline: same code revision, data slice, shapes, precision, seeds, environment, and warmup.
- Measure end-to-end wall-clock time over completed work. For asynchronous backends, synchronize relevant execution at measurement-window boundaries and preserve normal overlap inside the window. Separate startup/compilation costs from steady-state timing; include startup in the end-to-end result when it materially affects the requested workload.
- Optimize only after bottleneck evidence; do not infer the layer from intuition.
- Choose the smallest experiment that answers the optimization question. Isolate one variable when attributing an effect; test coupled changes together when the expected gain depends on their interaction. Record the expected mechanism before running.
- Treat utilization as evidence, not the goal; the goal is useful throughput under correctness, stability, memory, and maintainability constraints.
- Report before/after with evidence paths, confidence, regressions, and next hypothesis. Never claim speedup from inspection alone.

## Universal Loop

1. **Fix the objective**: primary throughput metric, target, precision tolerance, convergence tolerance where applicable, memory limit, latency/SLA if any, hardware count/topology, time budget.
2. **Define the baseline workload**: representative shape list, batch/microbatch, sequence or domain size, optimizer, data pipeline, warm-up and measured windows.
3. **Estimate relevant bounds** when they help distinguish bottlenecks or assess remaining headroom. State the workload and assumptions behind each estimate.
4. **Decompose time**: trace input/host work, runtime overhead, kernels, communication, synchronization, and idle gaps; account for overlap.
5. **Classify the bottleneck**: compute-bound, memory-bound, communication-bound, input/host-bound, runtime/compile-bound, bubble-bound, memory-capacity-bound, numerics/stability-bound.
6. **Choose an intervention**: rank options by expected end-to-end gain, implementation effort, and numerical or semantic impact. Prefer suitable existing library/compiler implementations; consider custom kernels for measured hotspots when their expected benefit justifies implementation and maintenance costs.
7. **Run a targeted experiment**: hold unrelated workload and environment settings fixed; vary coupled settings together when required by the hypothesis.
8. **Validate**: numerical error, convergence trend where applicable, determinism needs, memory peak, throughput, tail latency, stability over longer runs.
9. **Promote or kill**: keep only if primary metric improves beyond noise and guardrails hold; otherwise revert and record the negative result.
10. **Re-profile**: the bottleneck usually moves after each accepted change.

## Bottleneck Decision Tree

Check measurement first; prioritize fixes by measured impact and cost.

1. Is the measured workload representative and stable? If not, fix measurement first.
2. Is input/host unable to feed the device? Check device idle gaps before device kernels.
3. Is memory capacity forcing small batch, recomputation, offload, or excessive fragmentation?
4. Is communication or synchronization on the critical path? Overlap, bucket, topology, parallelism, or precision of exchanged data may matter.
5. Are kernels memory-bound? Improve locality, fusion, layout, tiling, reuse, and precision before adding peak compute.
6. Are kernels compute-bound? Improve math library path, tile shape, pipeline, instruction mix, and only then consider exotic rewrites.
7. Are there bubbles from scheduling, dynamic shapes, graph breaks, serialization, or uneven pipeline stages?
8. Is numerics/convergence limiting usable speed? A faster unstable configuration is not throughput.

## Layer Map

Use this map to identify options and evidence across layers:

| Layer | Typical decisions | Main evidence |
|---|---|---|
| Objective/measurement | metric, shapes, window, warmup, noise bars | profiler summaries, logs, counters |
| Data/input | workers, prefetch, caching, tokenization or mesh loading, pinning/offloading | input wait, host utilization, device gaps |
| Runtime/compiler | eager vs graph, fusion, static shapes, memory pools, graph capture | framework time, graph breaks, launch overhead |
| Precision | FP64/FP32/TF32/BF16/FP16/FP8, scaling, accumulation | error metrics, loss curve, stability |
| Memory | checkpointing, offload, layout, allocator, workspace, activation footprint | peak memory, recompute time, copies |
| Parallelism | data, tensor, pipeline, sequence/context, expert, sharding | communication bytes, balance, bubbles |
| Communication | collectives, bucketing, overlap, topology, compression | comm time, imbalance, slow peer/link |
| Kernels/operators | hotspot rewrite, fusion, tiling, vectorization, pipeline, library call | kernel time, roofline gap, counters |
| Algorithm/model | architecture, sparsity, pruning, distillation, optimizer math | quality and convergence |

## Risk Classes

Classify each change by its actual effect on the computation; the techniques below are examples, not fixed classifications. For batching, accumulation, and parallelism changes, check effective batch size, loss normalization, optimizer/scheduler update cadence, and batch-dependent operations. Changes to these semantics belong in Class C; changes limited to floating-point evaluation belong in Class B.

- **Class A, performance-only**: measurement, caching, scheduling, layout, overlap, equivalent fusion, graph capture, memory placement. Accept after speed and correctness checks.
- **Class B, numerics-risk**: lower precision, changed reduction order, approximate kernels, different parallelism, gradient accumulation with unchanged training semantics. Check numerical error against task tolerances; check training or solver convergence where applicable.
- **Class C, objective/semantics**: model architecture, sparsity, pruning, distillation, compressed gradients, changed optimizer, sampling or data curriculum. Require explicit user approval and full validation.

Never present Class B/C as free performance. State the traded quantity: precision, convergence, reproducibility, memory, complexity, or portability.

## Experiment Card

Require every proposed change to be expressible as:

```text
Hypothesis: changing X reduces Y because Z is binding.
Scope: shapes/data/precision/hardware/backend versions held constant except declared decision variables.
Change: decision variables and rollback path.
Metrics: primary throughput; guardrails: memory, error/loss, stability, tail/imbalance.
Evidence: profile/counter/log paths before and after.
Decision: promote if improvement > noise and guardrails pass; otherwise kill.
```

## Backend Adaptation Rule

Collect only backend facts needed to diagnose the bottleneck or choose an intervention:

- execution units and their practical peak rates
- memory hierarchy capacities and bandwidths
- interconnect/collective model and topology
- profiler/trace sources and the counters that map to compute, memory, communication, overlap, bubbles
- compiler/runtime modes and their failure modes
- kernel authoring path and library alternatives
- precision formats and accumulation rules
- determinism and reproducibility constraints

## Common Failure Modes

- Optimizing kernels while input starvation creates device idle time.
- Adding parallel communication to fix a memory-capacity problem, making both worse.
- Chasing peak FLOPs while most time is copies, launches, synchronization, or imbalance.
- Accepting a lower-precision result without checking the real objective or science tolerance.
- Claiming speedup from uncontrolled workload or environment differences.
- Treating average throughput as sufficient when tail latency, slow peers, or pipeline imbalance dominates.
- Reporting utilization without useful throughput, or throughput without correctness.

## Required Output

For analysis or plans, return:

1. Objective and constraints.
2. Baseline definition and measured decomposition.
3. Bottleneck classification with evidence and confidence.
4. Relevant performance bounds and gaps, when they inform the next decision.
5. Ranked options with layer, expected mechanism, end-to-end gain, risk class, implementation and maintenance costs, and rollback.
6. Next targeted experiment card.

Keep plans short when evidence is missing: state what to measure first and why.
