<!--
PR Title Format: <type>(<optional scope>): <description>

Valid types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

Examples:
  feat(skills): add new aws-vpc-creator skill
  fix: correct frontmatter in issue-triage
  docs: update install instructions

The PR title is validated automatically.
-->

## Summary

<!-- What changed, why now, and the user or system impact. -->

## Changes

<!-- Concise bullets; call out intentionally omitted or deferred work. -->

-

## Validation

<!-- List commands/checks run and their result. State "Not run" with a reason if applicable. -->

- [ ] Ran validation: `task validate`
- [ ] Ran the full gate: `task lint`
- [ ] New/updated skills have valid `SKILL.md` frontmatter (`name` + `description`)
- [ ] Verified discovery: `task verify-discovery`

## Risk and rollout

<!-- Compatibility, security, data, infrastructure, cost, or operational impact. Include rollback/migration notes when relevant. -->

**Risk:** <!-- None / Low / Medium / High — explain -->

**Rollback / migration:** <!-- N/A or steps -->

## Agent disclosure

<!-- Complete only when an AI/coding agent materially contributed. The responsible human must still complete validation and risk. -->

- **Agent/tool:**
- **Human owner/reviewer:**
- **Agent contribution and human verification:**

## Reviewer notes

<!-- Focus reviewers on design decisions, trade-offs, or areas needing special attention. -->
