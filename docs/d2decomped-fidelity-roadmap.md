# D2Decomp fidelity roadmap and actionable checklist

Created 2026-10-28 from the [baseline review](d2decomped-fidelity-review-2026-10-28.md). This is a proposed work backlog, not authorization to implement or publish changes. All unchecked boxes are future work. Reconcile them against current upstream before starting; the baseline is commit `6fc2820edd3c4712690f9fa454b9f595c3e7ea68`.

## Working rules and definition of done

- [ ] Assign an owner and tracking issue to each selected task before implementation.
- [ ] Pin the source commit, original executable SHA-256, data/patch identity and tool versions for each investigation.
- [ ] Keep original bugs, port regressions, intended differences, missing features and unknowns separate.
- [ ] Require every behavior fix to include original evidence, a failing-before regression test, current documentation and a residual-unknown statement.
- [ ] Require asset-backed checks to report executed, skipped and failed separately.
- [ ] Keep copyrighted binaries, extracted game data and derived bulk disassembly outside public source history.
- [ ] Keep mod-specific work in the separate mods repository, per `../AGENTS.md`.
- [ ] Update the review and generated status after each completed milestone; retain prior snapshots.

## Sequence and priorities

| Stage | Priority | Depends on | Deliverable / exit gate |
|---|---|---|---|
| M0: evidence and status | P0 | None | Reproducible baseline and linked registries |
| M1: natural campaign | P0 | M0 identifiers | Reproducible organic classic and LoD campaigns; failures catalogued |
| M2: visible gaps | P1 | M0; M1 findings | No unresolved high-severity single-player omission |
| M3: subsystem equivalence | P1 | M0; can overlap M1/M2 | Bounded differential reports and explicit unknowns |
| M4: presentation | P2 | M0; M3 format findings | Asset traversal and measured visual/audio comparisons |
| M5: multiplayer | P2 | M0; per-player quest groundwork | Hosted campaign and mixed-client compatibility reports |
| M6: release readiness | P2 | Relevant earlier gates | Reproducible desktop release and documented limitations |

Prioritize save loss, crashes and progression blockers immediately when found, regardless of stage. No calendar estimate is justified until the first campaign run and subsystem inventory reveal the actual defect workload.

## M0 — Establish measurable status

- [ ] Reconfirm upstream HEAD and freeze a review checkout; record whether local changes exist.
- [ ] Inventory existing tests, oracle scripts and retained RE evidence before creating replacements.
- [ ] Review tool behavior and assumptions before running it; fix relevant weaknesses in an isolated tooling change and verify them first.
- [ ] Create a machine-readable requirement ledger with stable IDs, subsystem, original/port behavior, status, confidence, evidence, test, owner and last-verified commit.
- [ ] Create linked registries for original defects, introduced regressions, intentional deviations and missing/removed features.
- [ ] Map all existing bugs.md, deviations.md, unverified.md, stubs.md and todo.md entries to ledger IDs.
- [ ] Classify each `ponytail:` note; distinguish fidelity gaps from code organization/performance debt.
- [ ] Extend the function catalogue with semantic status, signatures/structures, implementation mappings, oracle/test links and remaining unknowns.
- [ ] Define content, behavioral, presentation, compatibility and readiness denominators independently.
- [ ] Separate reachable content from unused/stubbed/realm-only content in coverage totals.
- [ ] Repair duplicate original-bug IDs and preserve aliases for old citations.
- [ ] Reconcile sound totals, debt counts, toggle documentation and test README claims.
- [ ] Move historical checkpoints behind an explicit historical label and publish a concise current-state index.
- [ ] Generate summary tables from the ledger and add consistency checks for stale references/counts.
- [ ] Save reusable tools persistently with purpose, invocation, input requirements and failure behavior documented.

Acceptance: every public completion statement resolves to a baseline, denominator and evidence; unknown values stay unknown. A green test report shows which original/data-backed checks actually ran.

## M1 — Prove natural campaign progression

- [ ] Implement the click-only campaign driver proposed in [#83](https://github.com/psi29a/d2decomped/issues/83); permit observation but no debug mutation of quest/progression state.
- [ ] Use isolated saves/configuration and guarantee process/socket cleanup on success, failure and timeout.
- [ ] Complete a new-character classic Normal campaign through Diablo.
- [ ] Complete a new-character LoD Normal campaign through Baal.
- [ ] Retain input replay, seed, character/build, saves, timestamps, logs and milestone screenshots for each run.
- [ ] Verify natural quest prerequisites, item acquisition/use, NPC menus, travel, endings and difficulty unlocks.
- [ ] Exercise death/corpse recovery, mercenary death/revive, town portals, waypoint travel, interruption and save/reload at selected quest boundaries.
- [ ] Record each failure with reproduction, severity and an introduced-regression/unknown ID.
- [ ] Repeat using a documented seven-class build matrix; include melee, ranged, caster and summon behavior.
- [ ] Extend representative campaigns to Nightmare/Hell, hardcore and classic/LoD save interchange boundaries where supported.

Acceptance: reproducible organic classic and LoD completions, with all setup shortcuts disclosed and no unresolved progression blocker in the selected scenarios. Broader class/difficulty claims require their corresponding runs.

## M2 — Close visible gameplay omissions

- [ ] Complete charged-item skill registration, picker, casting, depletion, socketed sources, tooltip and repair behavior ([#85](https://github.com/psi29a/d2decomped/issues/85)).
- [ ] Trace and implement MonEquip selection, including Valkyrie level-dependent gear.
- [ ] Verify MonItemPercent and equipped-monster drop behavior against the original.
- [ ] Inventory per-skill gaps and rank by reachability, severity and player impact.
- [ ] Trace Council S1 event timing and unresolved unique modifiers/boss-death paths; classify disabled thief behavior as unreachable where supported by evidence.
- [ ] Replace consequential RNG stand-ins with the correct original streams; test seed progression as well as outcome.
- [ ] Match town portal free-spot selection and blocked-placement behavior.
- [ ] Match special/uber-level population and object groups, separately documenting offline portal/AI stubs.
- [ ] Close high-severity defects discovered by M1 and retain regression scenarios.

Acceptance: no known high-severity single-player omission in the defined scope; every deferred skill/edge case has an ID and explicit player impact.

## M3 — Establish subsystem equivalence

- [ ] Define a corpus for DRLG, objects, monsters/AI, combat, skills, items/drops, quests, saves, UI/CLI and networking.
- [ ] Assign function/table anchors and map them to port implementations and tests.
- [ ] Record emulator hooks, replaced callees, artificial state and unsupported operations as oracle limitations.
- [ ] Run differential tests with normal inputs, boundaries, invalid inputs where relevant and multiple deterministic seeds.
- [ ] Compare state changes, events and RNG consumption, not just return values.
- [ ] Use focused decompilation for unresolved mismatches and runtime observation for questions static analysis cannot settle.
- [ ] Export retained evidence with stable identities before closing analysis sessions.
- [ ] Distinguish discovery/naming coverage from behavior verification; never count generic names as proof of ignorance or incompleteness.
- [ ] Publish subsystem counts: requirements tested, matched, mismatched, intentionally different, skipped and unknown.
- [ ] Verify save compatibility beyond existing fixtures, including truncation, corrupt checksums, foreign character identity and interrupted writes.

Acceptance: each subsystem has a bounded, reproducible report with explicit test corpus and remaining unknowns. Passing selected functions does not establish whole-game equivalence.

## M4 — Measure presentation and finish audio

- [ ] Re-audit reachable sound triggers before treating every unused row as a missing sound.
- [ ] Finish reachable quest voices/jingles, NPC lines and code-triggered sounds ([#87](https://github.com/psi29a/d2decomped/issues/87)).
- [ ] Finish skill progress/monster start, block, kick and remaining state/event cues; correct camp material footsteps.
- [ ] Compare audio trigger timing, sequence events, spatial falloff, pan, loops, interruption and pause behavior.
- [ ] Build an animation tour covering each class/weapon/mode, monster, object, missile and overlay; record reached and unreachable assets separately.
- [ ] Compare timing against AnimData and verify short/missing-layer compatibility decisions.
- [ ] Trace COF alpha modes and evaluate PL2 blending, tile interpolation, composite shadows and static-light shadows.
- [ ] Verify overlay light/wait behavior and Act IV clock/eclipses.
- [ ] Capture original/port scenes at fixed resolution, camera, seed, clock and state; define image regions/masks and report metric limitations.
- [ ] Document faithful defaults and every visual/audio toggle, including defaults and non-toggleable differences.

Acceptance: presentation reports measure behavior and traversal, with known approximations listed; asset parsing alone does not count as visible correctness.

## M5 — Complete networking compatibility

- [ ] Finish live joined-game validation for Act V and outstanding packet/UI effects in Acts I–IV.
- [ ] Make quest state and credit per-player before network hosting depends on it.
- [ ] Implement d2d TCP/IP hosting and client join/leave lifecycle.
- [ ] Implement the standalone dedicated server.
- [ ] Test campaign progression with two d2d clients and a d2d host.
- [ ] Test the supported mixed original/d2d combinations and document unsupported combinations.
- [ ] Cover trade, drops, corpses, death, portals, waypoints, party XP/gold, disconnects, save-back and host failure.
- [ ] Trace or explicitly classify current timeout, drift-correction and autoparty policies.
- [ ] Maintain a separate local-co-op behavior matrix; do not use it as evidence of original network parity.
- [ ] Keep Battle.net/realm support explicitly out of scope unless separately approved and baselined.

Acceptance: a hosted campaign succeeds reproducibly; mixed-client claims identify exact versions and tested scenarios; protocol differences and limitations are published.

## M6 — Release readiness and ongoing reporting

- [ ] Verify high-DPI behavior and supported display/window configurations.
- [ ] Validate packaging/install/update on Linux, Windows and macOS with documented minimum versions.
- [ ] Run long-session, repeated new-game/load/quit and arbitrary save-boundary tests.
- [ ] Establish startup, memory, frame-time and simulation budgets with reproducible benchmarks.
- [ ] Verify crash-report consent, packaging and symbolication according to the project's existing design.
- [ ] Adopt changelog sections for features, port regressions fixed, original bugs fixed, compatibility changes, removals and known issues.
- [ ] Link changelog entries to ledger IDs, tests and fixed commits, following DevilutionX's useful category separation.
- [ ] Publish release-specific fidelity snapshots and residual unknowns; do not present experimental platform support as validated.
- [ ] Expand mobile/console work after its own feasibility and validation gates, independently from fidelity percentages.

Acceptance: reproducible desktop packages, completed required validation and release notes that state tested scope, intentional differences and remaining defects.

## First work batch

- [ ] Refresh and freeze the baseline.
- [ ] Create the ledger schema and migrate the four existing research registries plus stubs.
- [ ] Fix the documentation inconsistencies flagged in the review.
- [ ] Make skipped asset-backed tests visible as skips in reports.
- [ ] Produce one natural Normal LoD run and triage its failures before expanding the backlog.

## Task card template

Copy this for each implementation or investigation task:

```markdown
- [ ] <ID>: <observable outcome>
  - Priority / owner / issue:
  - Depends on:
  - Baseline commit / executable hash / data identity:
  - Original behavior and evidence:
  - Current port behavior and reproduction:
  - Status category / confidence:
  - Planned change or investigation:
  - Acceptance criteria:
  - Failing-before test / differential scenario:
  - Verification result, including skips:
  - Fixed commit / evidence bundle / updated documents:
  - Remaining unknowns:
```
