---
type: SourceLocationRFC
title: Source-location contract decision
description: Retains logical line locations as the supported source coordinate system and defers byte and column offsets until a named consumer requires them.
status: stable
classification: canonical
audience: maintainers
owner: logseq-matryca-parser
authority: source_repository
execution_mode: reviewed
last_verified: 2026-08-20
verified: 2026-08-20
stale_after: 2027-02-18
okf_profile: matryca_okf_inspired_quality
okf_spec_version: null
supersedes: null
superseded_by: null
decision_date: 2026-08-18
---

# Source-location contract decision

## Status

Accepted on 2026-08-18 and shipped in v1.8.0. M6 records a deliberately small source-location
contract and rejects a new byte-, code-point-, or column-offset prototype for
the current release line.

## Context

The parser already attaches `line_start` and `line_end` to every
`LogseqNode`. Three maintained consumers rely on those logical line locations:

- structured diagnostics expose a one-based `Diagnostic.line` while preserving
  vault-relative path safety;
- the bounded writer uses the deepest `line_end` to choose its safe splice
  insertion point; and
- SYNAPSE includes `line_start` in lineage metadata for downstream retrieval.

These consumers need a stable human-readable position, not a character-level
editor protocol. Adding offsets now would require resolving byte encoding,
Unicode scalar/code-point/grapheme semantics, CR/LF normalization, transformed
content, serialization drift, and stale-source behavior without a named
consumer that can prove the added compatibility and maintenance cost.

## Decision

Retain the existing logical line model as the only supported source coordinate:

| Field | Contract |
|---|---|
| `LogseqNode.line_start` | One-based inclusive logical line where the node begins. |
| `LogseqNode.line_end` | One-based inclusive logical line through the node's parsed properties, continuation text, fenced/query regions, and other absorbed lines. |
| `LogseqNode.source_path` | Parser-source path when the parse entry point has one; consumers exposing diagnostics must normalize it to a vault-relative POSIX path. |

`StackMachineParser.parse()` enumerates logical input lines. CRLF is treated as
one logical line break; Unicode content does not change line counting. These
locations are parse-snapshot metadata, not durable editor anchors: after a
source file changes, a consumer must reload/reparse before using a location.

Do not add public byte offsets, code-point offsets, columns, ranges, or a
source-map object in this milestone. The existing fields stay unchanged and
their semantics are clarified by regression tests only; no package-root API,
serialization schema, parser algorithm, or runtime dependency changes.

## Evidence

- `tests/test_logos_parser.py` proves one-based start/end lines across Unicode
  content and CRLF input, including absorbed property and continuation lines.
- Existing deep-refresh tests prove that `line_end` advances with soft breaks
  and property families.
- Existing writer tests prove that a parsed `line_end` drives a bounded child
  splice, including a source lacking its final newline.
- Existing diagnostics and SYNAPSE tests prove the current line metadata is
  exposed to their respective consumers.

## Non-goals and future admission gate

This is not a promise of precise ranges into transformed `content` or
`clean_text`, editor selection behavior, UTF-8 byte slicing, or stable
locations across watcher refreshes and writes. A future expansion requires all
of the following:

1. a named downstream consumer with a concrete failure that line locations
   cannot solve;
2. an accepted successor RFC defining coordinates, newline and Unicode rules,
   stale-range semantics, serialization provenance, and memory budget;
3. focused non-ASCII, CRLF, malformed-input, parse/serialize/reparse, writer,
   and consumer compatibility tests; and
4. measured parser and graph impact with no regression of the existing line
   contract.

Until then, use node UUIDs and outline paths for identity and `line_start` /
`line_end` only for the parse snapshot that produced them.
