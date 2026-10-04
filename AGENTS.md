
- Never read from or write to `docs/scratchpad.md`. The user copies relevant requirements into the conversation.
- Graphify is optional local developer tooling. Install it once with `bin/graphify-setup`; its generated `graphify-out/` directory is never committed.
- For architecture, dependency, or change-impact questions, run `bin/graphify query "<question>"` when a local graph is available. Use `bin/graphify update .` only when refreshing the local graph is useful.
