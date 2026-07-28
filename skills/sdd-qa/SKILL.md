---
name: sdd-qa
description: "Ask SDD spec clarification questions ONE-by-ONE and write decisions back to the questions file. Slash-command only."
disable-model-invocation: true
---

# SDD Q&A

Ask me questions from the spec questions file ONE-by-ONE and write the decision and any additional context back to the question file.

## Resolve the file

```bash
python3 {{skill_dir}}/scripts/find-questions.py <spec-or-glob>
```

`<spec-or-glob>` = user arg, path, `01`, feature slug, or glob like `01*questions.md`. Cwd = workspace root. If 0 or >1 matches, ask which file.

## Run the loop

1. Read `{{skill_dir}}/references/qa-format.md` — follow its response + file-write formats exactly.
2. Find the first unanswered question (no `**Decision:**`, or all options still `[ ]`).
3. Ask **only that question**. Wait.
4. On a clear choice: write decision + context into the file, then ask the next.
5. Clarifying questions mid-flow: answer them; do **not** advance until they pick.
6. After the last answer: write a decision summary table (see reference).
