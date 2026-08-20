# skills

[![skills.sh](https://skills.sh/b/SystemFiles/skills)](https://skills.sh/SystemFiles/skills)

Agent skills I've built or augmented from other sources, packaged as a [skills.sh](https://www.skills.sh/) source you can install from with the [`skills` CLI](https://github.com/vercel-labs/skills).

Each skill is a directory under `skills/<name>/` containing a `SKILL.md` (plus any helper scripts/evals). The `skills` CLI installs them into whichever AI coding agents you have (Cursor, Codex, Claude Code, and [many more](https://github.com/vercel-labs/skills#supported-agents)).

## Available skills

### Authored here

| Skill | Description |
| --- | --- |
| `issue-triage` | Turn a rough GitHub Issue into an agent-executable sealed body with `ready` + size labels (explicit invocation). Clarifying Q&A persists under `.issue-triage/` (gitignored) for resume. Ships `issue_ops` + validators, offline `evals/`, and `mock_gh` for script unit tests. |
| `bro` | Slash-command only (`/bro`): restate the last message plainly and concisely, without jargon. |
| `jj-case-insensitive-clone-fix` | Diagnose and fix the `jj git clone` "Failed to update refs" error on case-insensitive filesystems (e.g. macOS APFS). |
| `pr-feedback-qa` | Disposition PR or file-based review feedback one item at a time (Address / Skip / GitHub Issue), with resumable JSON sessions under `.scratch/pr-feedback-qa/` and a final decision table. |
| `research_codebase` | Map how a codebase works today and save a dated, citation-backed report under `thoughts/`, using parallel sub-agents by default. |
| `sdd-qa` | Ask SDD `docs/specs` clarification questions ONE-by-ONE and write decisions back to the questions file (explicit slash invocation). |
| `sykesdev-design-system` | Apply the sykesdev Harbor Chart design system to app UI, pages, and fully self-contained single-file HTML documents. Ships tokens, a component + behavior layer, self-hosted fonts, the mark, a document starter, `bundle_html.py` (inline everything into one sendable file) and `render_check.py` (tmp screenshots for judging, not shipping). |
| `sync-upstream` | Sync a fork's default branch with its upstream remote using merge or rebase, resolving conflicts as needed. |
| `visual-explain` | Interactive local HTML explanation of a diff/branch/PR (Background, Intuition, Code walkthrough, Quiz). Adapted from sighup/claude-workflow `cw-explain`. |

### Vendored from upstream

These skills are copied verbatim from their upstream repositories and kept fresh
automatically, so they install from this one source alongside the authored
skills. They are declared in [`upstream-skills.toml`](upstream-skills.toml),
copied in by `scripts/sync_upstream_skills.py`, and refreshed on a schedule by
the [Sync Upstream Skills](.github/workflows/sync-upstream-skills.yml) workflow.
Do not hand-edit `skills/<name>/` for these; change the catalog instead.
Provenance (source commit and license) is recorded in `upstream-skills.lock.json`.

| Skill | Upstream | License | Description |
| --- | --- | --- | --- |
| `code-review` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Two-axis review (Standards + Spec) of changes since a commit, branch, tag, or merge-base. |
| `codebase-design` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Shared vocabulary for designing deep modules (interfaces, seams, testability). |
| `domain-modeling` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Build and sharpen a project's domain model (`CONTEXT.md` / ADRs). |
| `grill-me` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Relentless interview to sharpen a plan or design (explicit invocation). |
| `grill-with-docs` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Same grilling loop, also producing ADRs and glossary docs as you go. |
| `grilling` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Stress-test a plan/decision/idea with a decision-tree interview. |
| `improve-codebase-architecture` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Scan for deepening opportunities, present an HTML report, then grill one. |
| `prototype` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Throwaway logic or UI prototype to answer a design question. |
| `research` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Investigate a question against primary sources and write findings as Markdown in the repo. |
| `tdd` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Test-first / red-green-refactor workflow with seam-based tests. |
| `teach` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Teach a skill or concept inside the current workspace. |
| `to-spec` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Synthesize the current conversation into a spec and publish it (explicit invocation). |
| `to-tickets` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Break a plan, spec, or conversation into tracer-bullet tickets with blocking edges (explicit invocation). |
| `wayfinder` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Map large work as decision tickets on an issue tracker and resolve them one by one. |

## Install

Prefer [`bun`](https://bun.sh) / `bunx` over `npm` / `npx`.

List the available skills without installing:

```bash
bunx skills add SystemFiles/skills --list
```

Install a single skill (interactive agent selection):

```bash
bunx skills add SystemFiles/skills --skill issue-triage
```

Install to specific agents (e.g. Cursor and Codex):

```bash
bunx skills add SystemFiles/skills --skill issue-triage -a cursor -a codex
```

Install non-interactively (CI-friendly):

```bash
bunx skills add SystemFiles/skills --skill issue-triage --yes
```

Install globally (available across all projects) instead of into the current project:

```bash
bunx skills add SystemFiles/skills --skill issue-triage --global
```

Install every skill in this repo:

```bash
bunx skills add SystemFiles/skills --skill '*'
```

### Cursor plugin (IDE / team / Cloud Agents)

This repo is also an [Agent Plugin](https://agent-plugins.org): root [`plugin.json`](plugin.json) plus `skills/*/SKILL.md`. Prefer this path when you want Cursor (not other agents) to load the whole catalog without the skills CLI.

Local dry-run:

```bash
ln -s "$(pwd)" ~/.cursor/plugins/local/systemfiles-skills
```

Reload Cursor, then confirm skills under Customize.

Team Marketplace (Teams / Enterprise): Dashboard → Plugins → import this GitHub repo → set Required or Default On. Enable auto-refresh if the Cursor GitHub App is on the repo.

Cloud Agents do not see `bunx skills add --global` home installs. After marketplace install, verify a Cloud Agent can invoke a skill from this catalog. If it cannot, commit the needed skills under `.agents/skills/` or `.cursor/skills/` in the target repo (project-scoped discovery).

## Updating and removing

```bash
# Update installed skills from this source
bunx skills update

# Remove a skill
bunx skills remove issue-triage
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to add or update a skill, run validation (`task validate`), and the commit/PR conventions.
