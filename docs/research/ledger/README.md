# Research ledger

This is an index of the existing research records at `564ec10d`, plus the
2026-10-27 CodeRabbit audit of PRs #15–#97 and five port defects recorded
in the 2026-10-28 review follow-ups. It preserves each source row and
its uncertainty. It does not establish a whole-game fidelity denominator.
The Markdown research files remain the detailed evidence and policy record.

| File | Scope |
|---|---|
| requirements.toml | Stable requirement IDs linked to one registry record each |
| original-bugs.toml | Every bugs.md row, including suspicions and findings called not a bug |
| deviations.toml | Improvements, approximations and additions, including historical matches |
| missing.toml | todo.md table rows and separately identified original stubs/dead code |
| unverified.toml | Unverified rows and their separately identified Traced history |
| regressions.toml | 189 valid/valid-minor audit findings plus five recent port defects; includes tooling and documentation defects |

The same behavior can appear in several source lists. Requirement rows mirror
registry records; neither count is a count of independent verified behaviors.
Stubs in the selected offline original are not missing port features. No
historical removed-feature inventory or complete prose/source-comment inventory
has been established. In particular, todo.md's prose-only joined-game gaps and
its long tail of `ponytail:` notes remain outside this initial table migration.

## Schema version 1

Each file has `schema_version`, `indexed_at_commit`, `imported_on` and
`provenance`, followed by `[[entry]]` records. Each entry contains:

- `id`, `title`, `subsystem`: stable identity and scope; unclassified scope stays explicit.
- `original_behavior`, `port_behavior`: bounded descriptions or explicit unknowns.
- `status`: unknown, documented, traced, reported-fixed, reported-open or retracted.
- `confidence`: unknown, documented or review-reported. Source confidence wording
  is retained in `source_cells`; documentation is not a new verification.
- `evidence`, `tests`: repo-relative files or HTTPS references. Empty tests means
  no test was assigned during migration; it does not mean no test exists.
- `owner`: unassigned until someone accepts the work.
- `last_verified_commit`: unknown until the behavior is checked at a full commit SHA.
- `links`: reciprocal requirement/registry links; additional related IDs may be added.
- `aliases`: old citations, qualified by source and section to avoid ambiguity.

Source-table entries additionally retain `source_key`, `source_sha256`,
`source_columns`, `source_cells` and `source_kind`. The fingerprint detects
changes to any cell. Retain IDs when wording changes. Section or first-cell
changes require updating the source key and keeping its old value as an alias.
`OB-0034` retains `bugs.md#16:missile-path-room`; the town NPC remains `OB-0016`.

Audit entries retain their thread ID (`CR-<GitHub comment ID>`), affected path,
category, verdict, reported resolution/fix and suggested detection method.
Fix ranges and reply-derived SHAs are preserved verbatim as `reported_fix`;
they are not last-verified commits. These are introduced port/tool/doc defects,
not proof of a regression from a previously correct release. First affected
versions, severity, platform and residual unknowns need investigation per entry.
Invalid and unclear audit findings are excluded. Public thread links preserve
provenance without publishing the local audit dumps or game assets.

## Maintaining and checking

Use Python 3.11 or newer (standard library only):

```
python3 tools/ledger.py --check
python3 tools/ledger.py --summary
python3 tools/ledger.py --write-summary
python3 -m unittest discover -s tools -p test_ledger.py
```

The checker is read-only unless `--write-summary` is explicit. It returns 1
for malformed TOML/schema, duplicate IDs/aliases, dangling links, missing local
references, missing/stale source rows or a stale summary. It never fetches URLs,
executes evidence, or claims a linked test passed. CTest runs `research_ledger`
when its Python interpreter is at least 3.11; older Python still runs existing
game tests and CMake reports that ledger checking needs a newer interpreter.

When a source row is resolved, retain it with historical status instead of
deleting it, update its ledger entry and reciprocal requirement, and regenerate
SUMMARY.md. Existing source policies that say to delete resolved todo rows are
superseded by this retention rule. New IDs are allocated once and never reused.
The initial migration is complete. Maintain assigned IDs in place; do not
regenerate them from table positions.
