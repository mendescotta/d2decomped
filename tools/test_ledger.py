#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the ledger's failure paths without game data or builds."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('ledger', Path(__file__).with_name('ledger.py'))
ledger = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ledger)
ROOT = Path(__file__).resolve().parents[1]


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'docs/research', self.root / 'docs/research')

    def replace(self, filename, old, new):
        path = self.root / 'docs/research/ledger' / filename
        text = path.read_text(encoding='utf-8')
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding='utf-8')

    def test_snapshot_and_summary(self):
        records, counts = ledger.check(self.root)
        self.assertEqual(counts['regressions'], 194)
        self.assertEqual(sum(identity.startswith('CR-') for identity in records), 189)
        self.assertEqual(counts['requirements'], sum(counts.values()) // 2)
        self.assertEqual(ledger.summary(records, counts), (self.root / 'docs/research/ledger/SUMMARY.md').read_text(encoding='utf-8'))

    def test_stale_source(self):
        path = self.root / 'docs/research/re/bugs.md'
        path.write_text(path.read_text(encoding='utf-8').replace('It declares 14', 'It declares fourteen'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source row changed'):
            ledger.check(self.root)

    def test_unmapped_source(self):
        path = self.root / 'docs/research/re/bugs.md'
        with path.open('a', encoding='utf-8') as stream:
            stream.write('\n## Additional\n| # | What |\n|---|---|\n| 99 | New observation |\n')
        with self.assertRaisesRegex(ValueError, 'unmapped source rows'):
            ledger.check(self.root)

    def test_dangling_link(self):
        self.replace('requirements.toml', '"OB-0001"', '"OB-9999"')
        with self.assertRaisesRegex(ValueError, 'dangling link'):
            ledger.check(self.root)

    def test_duplicate_id(self):
        self.replace('original-bugs.toml', 'id = "OB-0002"', 'id = "OB-0001"')
        with self.assertRaisesRegex(ValueError, 'duplicate id'):
            ledger.check(self.root)

    def test_unknown_status(self):
        self.replace('original-bugs.toml', 'status = "documented"', 'status = "verified"')
        with self.assertRaisesRegex(ValueError, 'invalid status'):
            ledger.check(self.root)

    def test_missing_evidence(self):
        self.replace('original-bugs.toml', '"docs/research/re/bugs.md"', '"missing.md"')
        with self.assertRaisesRegex(ValueError, 'missing or unsafe reference'):
            ledger.check(self.root)

    def test_duplicate_alias(self):
        path = self.root / 'docs/research/ledger/original-bugs.toml'
        text = path.read_text(encoding='utf-8')
        aliases = [line for line in text.splitlines() if line.startswith('aliases = ')]
        path.write_text(text.replace(aliases[1], aliases[0], 1), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate alias'):
            ledger.check(self.root)

    def test_retained_cells(self):
        self.replace('original-bugs.toml', 'source_cells = ["1"', 'source_cells = ["999"')
        with self.assertRaisesRegex(ValueError, 'retained source cells'):
            ledger.check(self.root)

    def test_invalid_schema(self):
        self.replace('original-bugs.toml', 'schema_version = 1', 'schema_version = 2')
        with self.assertRaisesRegex(ValueError, 'unsupported schema_version'):
            ledger.check(self.root)


if __name__ == '__main__':
    unittest.main()
