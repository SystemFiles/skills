---
name: github-pr-workflow
description: Create or update GitHub issues and pull requests for SystemFiles repositories using the shared templates, plain concise writing, and Conventional Commits. Use when authoring an issue, branch, commit, or PR.
---

# GitHub PR Workflow

Use this workflow for Ben's GitHub issues and pull requests.

## Before changing files

1. Read repository guidance and check the working tree.
2. Check for a repository-specific template. Otherwise use https://github.com/SystemFiles/.github.

## Issues

Use the issue template:

- Summary
- Acceptance Criteria (if applicable)
- Additional sources / Notes (if applicable)

## Pull requests

Use the PR template:

- Why
- What changed — a table mapping each acceptance criterion to its implementation
- Additional notes or context

## Writing rules

- Be extremely concise. Even sacrifice grammar for the sake of concision.
- Stop using jargon and speak coherently. State it more simply and concisely, like one human talking to another.

## Git rules

1. Create a focused branch.
2. Use Conventional Commits for commit messages and PR titles: `<type>(<optional scope>): <description>`.
3. Run relevant validation.
4. Push the branch and open or update the PR. Do not merge it unless asked.
