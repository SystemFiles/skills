---
name: work-breakdown
description: Analyzes a large piece of scope / work and provides recommendations on how to split the work into smaller units of work, identifying dependencies and opportunities for parallelization. Use when given an ambiguous, high-level requirement that may span multiple discrete systems, projects, or repositories and needs to be decomposed before any design or implementation begins.
---

# Work Breakdown

Analyze the provided features/issues and produce a breakdown of work suitable for parallel or sequential execution.

## Process

1. **Gather context** — Fetch issue details and read relevant source using the `codebase-exploration` and `research_codebase` skills.
2. **Identify work units** — Split into independently deliverable units that can be verified manually or with tests.
3. **Map dependencies** — Which units depend on others? What must be sequenced vs parallelized?
4. **Assess risks** — Flag units that touch the same files, repos, entities, or layers (merge conflicts, network, data, etc.).
5. **Recommend execution order** — Which units can run in parallel, which must be sequenced.

## Output

- Work units with one-line descriptions
- Dependency graph (minimal visual: which blocks which)
- Risk flags
- Recommended implementation strategy

Do not make requirements or design decisions — identify the shape of the work.
