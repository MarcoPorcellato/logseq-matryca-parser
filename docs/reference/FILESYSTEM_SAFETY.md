---
type: FilesystemSafetyContract
title: Vault-bound filesystem safety contract
description: Canonical containment, atomic replacement, dry-run, metadata, and input-limit policy for graph-bound writes and asset reads.
status: stable
classification: canonical
audience: contributors
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-07
verified: 2026-08-07
stale_after: 2027-02-03
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
---

# Vault-bound filesystem safety contract

Graph-bound reads and writes treat the selected Logseq graph as a security
boundary. A path discovered in Markdown or cached in a node is not trusted merely
because parsing succeeded.

## Writer policy

`append_child_to_node` applies these checks:

1. Resolve the selected graph root and registered node source.
2. Require the real source to remain under the graph root and satisfy the
   tracked `pages/` or `journals/` Markdown policy.
3. Require a regular file and capture device, inode, size, and nanosecond mtime
   before reading.
4. Enforce configurable source-byte, content-byte, and outline-depth limits.
5. Build the complete replacement and unified diff in memory.
6. For an applied write, create and fsync a same-directory temporary file,
   preserving permission bits and, where exposed by the platform, owner and
   group. Preservation failure aborts before replacement.
7. Resolve and stat the target again immediately before `os.replace`; reject
   path escape, symlink replacement, or identity/content change.
8. Atomically replace the target and only then refresh the in-memory graph.

External symlink targets are rejected. A symlink whose real target remains
inside the selected vault resolves to that in-vault target. Cross-process
locking remains outside this contract and belongs to snapshot/mutation work.

## Preview and limits

```python
from logseq_matryca_parser.agent_writer import append_child_to_node

proposal = append_child_to_node(
    graph,
    target_uuid,
    "candidate child",
    dry_run=True,
    max_source_bytes=8 * 1024 * 1024,
    max_content_bytes=1024 * 1024,
    max_target_depth=128,
)
assert proposal.path.is_relative_to(graph.graph_path)
print(proposal.unified_diff)
```

Dry-run performs all validation and diff construction but creates no temporary
file, performs no replacement, and does not reload the graph. KINETIC exposes
the same behavior through `agent-write --dry-run` and accepts matching limit
options.

## Failures and diagnostics

`VaultWriteError` carries one safe `Diagnostic`. Its stable codes are:

| Code | Meaning |
|---|---|
| `writer.vault_escape` | Real target is outside the vault, untracked, or not a regular file |
| `writer.target_changed` | Device, inode, size, mtime, or resolved target changed before replacement |
| `writer.input_limit_exceeded` | Configured source, content, or depth limit was exceeded |

Diagnostics never include an absolute external path. A source path is present
only when it can be proven vault-relative.

## Asset reads

`LogseqPage.resolve_asset_path` applies the same real-path containment rule to
relative links, `assets/` fallbacks, symlinks, and `file://` URIs. It returns an
absolute path only for an existing target inside the graph; external or missing
targets return `None`.
