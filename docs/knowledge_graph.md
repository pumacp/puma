# Code knowledge graph (GitNexus)

## What it is

PUMA's code is indexed into a queryable **knowledge graph** by
[GitNexus](https://www.npmjs.com/package/gitnexus), a local code-intelligence
tool. GitNexus parses the repository with Tree-sitter, builds a graph of symbols
(files, classes, functions, methods) and their relationships (calls, imports,
inheritance), groups them into clusters and execution flows, and exposes the
result to AI coding assistants and to humans. It runs entirely locally — the
index is built on-machine with no source upload.

It is surfaced three ways:

- **Skills** — project-scoped skill files under `.claude/skills/gitnexus/`
  (`gitnexus-guide`, `gitnexus-exploring`, `gitnexus-impact-analysis`,
  `gitnexus-debugging`, `gitnexus-refactoring`, `gitnexus-cli`). These load
  automatically in Claude Code.
- **MCP tools** — a local MCP server exposes `gitnexus_*` tools (`query`,
  `context`, `impact`, `detect_changes`, `route_map`, `rename`, …) for
  programmatic graph access.
- **CLI** — `npx gitnexus <command>` (`analyze`, `status`, `serve`, `wiki`, …).

## Why PUMA uses it

PUMA spans a six-layer architecture plus the modules added across Sprint 12 —
`ui/` (themes, banner, progress, errors, summary), `diagnostics/`, `models/`,
`runtime/retry`, and the `community/` channels surface. The graph lets an AI
coding assistant navigate callers/callees and execution flows without
re-grepping the whole tree, and lets it run **impact analysis before editing a
symbol** (the blast-radius check mandated in `CLAUDE.md`) rather than guessing.

## Current status

| Property | Value |
|---|---|
| GitNexus version | 1.6.3 |
| Last regenerated | 2026-05-26, against `develop` @ `67ee569` |
| Index location | `.gitnexus/` (gitignored, local-only; ~29 MB) |
| Files indexed | 337 |
| Nodes (symbols) | 5706 |
| Edges (relationships) | 8100 |
| Clusters | 148 |
| Execution flows | 75 |

The previous index (2026-05-16, `11ea00f`) predated most of Sprint 12 and read
3248 nodes / 4394 edges; the regeneration above brings the graph current with
the post-S12.13 surface. Run `npx gitnexus status` to check whether the index
has drifted from the current commit.

## How to use it

- **AI coding assistants (Claude Code, etc.):** the project-scoped skills under
  `.claude/skills/gitnexus/` load automatically; use the `gitnexus_*` MCP tools
  to query the graph, fetch a symbol's context, or run impact analysis. See
  `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` for the tool reference.
- **Humans:** inspect the graph locally with `npx gitnexus serve` (web UI) or
  generate a repository wiki with `npx gitnexus wiki`. `npx gitnexus status`
  reports the indexed commit and staleness.

## How to regenerate

From the repository root:

```bash
npx gitnexus analyze
```

This re-parses the working tree, rewrites the local index in `.gitnexus/`, and
refreshes the auto-generated GitNexus banner at the top of `CLAUDE.md`. Re-run
it whenever `npx gitnexus status` reports the index is stale (for example after
merging a branch that adds or moves modules).

## What is and isn't committed

| Committed (tracked) | Not committed (gitignored / local-only) |
|---|---|
| `.claude/skills/gitnexus/**` — the project-scoped skill set | `.gitnexus/` — the index database (~29 MB) |
| `docs/knowledge_graph.md` — this page | `CLAUDE.md` — auto-generated GitNexus banner |
| — | embeddings / pickled graph (none produced; not tracked) |

The index is intentionally local: it is fast to regenerate (a few seconds) and
machine-specific, so it is kept out of version control rather than committed.

## Related

For the wider knowledge-management context, see the
[PUMA Vault](https://github.com/pumacp/puma-vault).
