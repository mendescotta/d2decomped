# Review checklist: read your diff before the push

After `tools/presubmit.py` passes, read the branch's diff against this list:

    git diff upstream/main...HEAD

Read the code around each hunk, not just the hunk. Fix what you find in the
same push. Anything you leave on purpose gets one line in the PR body
("Not done: ..."), so the review doesn't raise it again.

Why: of the 189 valid CodeRabbit findings on PRs #15–#97, a linter or a
compiler flag would have caught about 6. A test would have caught 86, and
reading the diff against the list below 62.

## 1. Sibling paths (59 of 189)

The change reached one path and not its twins. For each rule the diff adds
or changes, list where else the same rule applies and check each one:

- unit kinds: player, co-op partner (`OtherPlayer`, replicated state), merc, pet/summon, monster, minion, boss/unique/superunique, skills a Shadow or Valkyrie owns;
- hit paths: melee strike, missile (the shooter's `shot_by`), skill, burner/aura, thorns, crush/knock;
- net roles: host, joined client, single player. Every send goes through the one sender (e.g. `Town::send`), not a raw `net.send`;
- acts 1–5, every difficulty, town and wild, expansion and classic;
- every consumer of a table, constant or slot range the diff widens (e.g. a portal slot range: town bounds, host lookup, the Esc chain);
- every mode a sequence or animation table covers (A1/A2/S1/SQ/KK/BL/...);
- every close/save/reset path of a feature: new game, leave, join end, co-op end, load, weapon swap.

## 2. Docs and comments (27)

- Every doc, README, todo.md row and comment that the diff touches, or that describes the changed code, still says what the code does: status (planned/done), counts, file paths, verb names, defaults, ports.
- No "all", "every" or "full parity" claim the code doesn't back. A comment or test name says no more than the code checks (#90: "or its leader gone" when only -1 was handled).
- devctl verbs changed → docs/control_channel.md; DRLG → drlg.md; sounds → unit-sounds.md.
- Markdown tables: the same cell count in every row; no stray spaces inside inline code.

## 3. State and logic (24)

- Every new member or flag: who resets it on new game, leave, co-op end and load? Who replicates it to the client?
- A new counter next to an old one (e.g. `seq_sounds` beside `seq_done`, #94): it is emptied wherever the old one is, or on every frame; it isn't consumed on a frame the old one skips (far from the players, dead).
- Event order: does a hit, death or drop happen before or after the state it reads?
- A choice that matches game.exe but looks wrong: cite the FUN_ address in a comment next to it. 10 findings were invalid for this reason alone; the comment heads them off.

## 4. Null, bounds, lifetime (14 + 9)

- `level()`, `town_of()`, finds and lookups: can they return null or end here?
- Index arithmetic: an empty container, `-1`, a not-found sentinel cast to `size_t`.
- Pointers or references into a vector that grows afterwards; `act_as` and other temporary overrides restored on every exit path.
- Files: the stream checked and closed before the rename; the replacement written before the old file is deleted.

## 5. Errors reach the exit status (12, tools 13, shell 8)

- C++: the return values of copy/mkpath/rename/close are checked; `std::filesystem`'s error_code overloads wherever a throw would escape.
- Python tools: argv validated up front; `subprocess.run(check=True)` or the return code checked; binary parsers check the length before indexing; patches and global state restored in `finally`; "nothing matched" is a nonzero exit, not success.
- Paths compared across sources (getcwd, compile_commands.json, ninja deps) go through `os.path.realpath`, not `abspath`: macOS's `/var` is `/private/var` (#91 failed only on the macOS leg).
- Shell: `set -euo pipefail`, quoting, a signal trap that exits, the cleanup trap on EXIT, background jobs stopped as a tree.

## 6. Tests (86 findings would have been caught by one)

- Each behaviour change has a test that goes through the real path (dispatch, devctl, the co-op link), not a debug shortcut.
- A fixture that needs 1.14d data is gated on `data->patched`; a test that needs MPQs SKIPs without them.
- The test fails on the old code (say how you checked).

## 7. CI parity

- A branch that touches C++ gets the full `tools/presubmit.py`, not `--quick`: quick skips clang-tidy, and an unused include reached CI that way (#94).
- Before the push, `tools/presubmit.py --docker` (or `tools/validate-linux.sh`) runs CI's Linux build, clang-tidy and tests.
- clang-tidy: every header the file uses is included (misc-include-cleaner); names have 3+ letters; no shadowed names (`-Wshadow`); no narrowing (`-Wconversion`).
