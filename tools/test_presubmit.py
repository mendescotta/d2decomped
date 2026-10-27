# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with: python3 -m unittest tools/test_presubmit.py"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("presubmit", Path(__file__).with_name("presubmit.py"))
presubmit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(presubmit)


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


class PresubmitTests(unittest.TestCase):
    def setUp(self):
        presubmit.results.clear()

    def levels(self, check):
        return [level for level, name, _ in presubmit.results if name == check]

    def test_short_names_as_clang_tidy(self):
        flagged = {"        const std::uint32_t at = 26 * kTickMs;": "at", "    auto c = foo();": "c",
                   "    const int n{3};": "n"}
        allowed = ["    for (const auto& x : xs)", "    int row = 0;", "    std::size_t i = 0;",
                   "    const auto& [a, b] = pair;", "    return a ? b : c;", "    bool ok = true;"]
        for text, name in flagged.items():
            self.assertEqual([hit.group(1) for hit in presubmit.SHORT_NAME.finditer(text)], [name], text)
        for text in allowed:
            names = [hit.group(1) for hit in presubmit.SHORT_NAME.finditer(text)]
            self.assertTrue(all(presubmit.SHORT_OK.match(name) for name in names), (text, names))

    def test_short_names_reports_added_cpp_only(self):
        presubmit.check_short_names({"a.cpp": [(3, "    auto c = 1;")], "b.py": [(1, "c = 1")]})
        self.assertEqual(self.levels("short-names"), ["FAIL"])
        presubmit.results.clear()
        presubmit.check_short_names({"a.cpp": [(3, "    auto count = 1;   // auto c = 1;")]})
        self.assertEqual(self.levels("short-names"), ["ok"])

    def test_added_lines_numbers_the_new_side(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q", "-b", "main")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "test")
            (root / "a.cpp").write_text("one\ntwo\nthree\n")
            git(root, "add", "a.cpp")
            git(root, "commit", "-q", "-m", "base")
            git(root, "checkout", "-q", "-b", "topic")
            (root / "a.cpp").write_text("one\nnew\ntwo\nthree\nlast\n")
            git(root, "commit", "-q", "-am", "change")
            numbers, texts = presubmit.added_lines(root, "main")
            self.assertEqual(numbers, {"a.cpp": {2, 5}})
            self.assertEqual(texts, {"a.cpp": [(2, "new"), (5, "last")]})

    def test_siblings_warn_on_one_unit_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            presubmit.check_review(Path(directory), "main", ["components/game/fight.cpp"],
                                   {"components/game/fight.cpp": [(10, "    if (player.alive()) hurt(player);")],
                                    "tests/test_game.cpp": [(5, "    assert(merc.alive());")]})
        warnings = [message for level, name, message in presubmit.results if name == "siblings"]
        self.assertTrue(any(message.startswith("unit kinds: the diff touches player,") for message in warnings), warnings)
        self.assertIn("test-gap", [name for _, name, _ in presubmit.results])

    def test_build_jobs_at_least_one(self):
        self.assertGreaterEqual(presubmit.build_jobs(), 1)
        self.assertGreaterEqual(presubmit.memory_cap_gb(), 4)


if __name__ == "__main__":
    unittest.main()
