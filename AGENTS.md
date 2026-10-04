
- Never read from or write to `docs/scratchpad.md`. The user copies relevant requirements into the conversation.
- Graphify is optional local developer tooling. Install it once with `bin/graphify-setup`; its generated `graphify-out/` directory is never committed.
- After Graphify is set up, run `bin/graphify query "<question>"` before answering codebase questions and `bin/graphify update .` after code changes.
