---
name: zed
description: Use when the user requests code is opened in the Zed IDE
---

# Zed

Open the code from the current session in the Zed IDE. We often work across multiple jj (Jujutsu) workspaces (roughly git worktrees), so open the active workspace's copy of the repo, not the root repo's location.

Check the CLI is installed:

```bash
command -v zed
```

Find the active workspace root (run from the directory the session is working in):

```bash
jj workspace root
```

Open it in Zed:

```bash
zed "$(jj workspace root)"
```

Outside a jj repo, pass the path of the active code directly: `zed <path>`.
