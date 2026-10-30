#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the ledger's failure paths without game data or builds."""
import importlib.util
import json
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

    def document(self, name):
        return json.loads((self.root / 'docs/research/ledger' / f'{name}.json').read_text(encoding='utf-8'))

    def write(self, name, doc):
        (self.root / 'docs/research/ledger' / f'{name}.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def change(self, name, edit):
        doc = self.document(name)
        edit(doc)
        self.write(name, doc)

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
        self.change('requirements', lambda doc: doc['entry'][0].update(links=['OB-9999']))
        with self.assertRaisesRegex(ValueError, 'dangling link'):
            ledger.check(self.root)

    def test_duplicate_id(self):
        self.change('original-bugs', lambda doc: doc['entry'][1].update(id='OB-0001'))
        with self.assertRaisesRegex(ValueError, 'duplicate id'):
            ledger.check(self.root)

    def test_unknown_status(self):
        self.change('original-bugs', lambda doc: doc['entry'][0].update(status='verified'))
        with self.assertRaisesRegex(ValueError, 'invalid status'):
            ledger.check(self.root)

    def test_missing_evidence(self):
        self.change('requirements', lambda doc: doc['entry'][0].update(evidence=['missing.md']))
        with self.assertRaisesRegex(ValueError, 'missing or unsafe reference'):
            ledger.check(self.root)

    def test_duplicate_alias(self):
        self.change('original-bugs', lambda doc: doc['entry'][1].update(aliases=doc['entry'][0]['aliases']))
        with self.assertRaisesRegex(ValueError, 'duplicate alias'):
            ledger.check(self.root)

    def test_retained_cells(self):
        self.change('original-bugs', lambda doc: doc['entry'][0]['source_cells'].__setitem__(0, '999'))
        with self.assertRaisesRegex(ValueError, 'retained source cells'):
            ledger.check(self.root)

    def test_invalid_schema(self):
        self.change('original-bugs', lambda doc: doc.update(schema_version=2))
        with self.assertRaisesRegex(ValueError, 'unsupported schema_version'):
            ledger.check(self.root)

    def test_metadata_required_and_typed(self):
        original = self.document('original-bugs')
        for field, invalid in (('indexed_at_commit', ('', 'abc', 1, None)),
                               ('imported_on', ('2026-02-30', '20261028', 1, None)),
                               ('provenance', ('', ' ', [], None)),
                               ('schema_version', (True, '1', None))):
            for value in invalid:
                with self.subTest(field=field, value=value):
                    doc = {**original, field: value}
                    if value is None:
                        del doc[field]
                    self.write('original-bugs', doc)
                    with self.assertRaises(ValueError):
                        ledger.check(self.root)
        self.write('original-bugs', original)

    def test_mirrored_fields(self):
        original = self.document('requirements')
        replacements = {'status': 'reported-open', 'confidence': 'unknown',
                        'last_verified_commit': '0' * 40,
                        'evidence': ['docs/research/re/deviations.md'],
                        'tests': ['docs/research/re/deviations.md']}
        for field in ('title', 'subsystem', 'original_behavior', 'port_behavior', 'status', 'confidence',
                      'owner', 'last_verified_commit', 'evidence', 'tests'):
            with self.subTest(field=field):
                doc = json.loads(json.dumps(original))
                doc['entry'][0][field] = replacements.get(field, 'different')
                self.write('requirements', doc)
                with self.assertRaisesRegex(ValueError, f'mirrored {field}'):
                    ledger.check(self.root)
        self.write('requirements', original)

    def test_one_requirement_per_record(self):
        self.change('original-bugs', lambda doc: doc['entry'][0]['links'].append('REQ-0002'))
        with self.assertRaisesRegex(ValueError, 'exactly one requirement'):
            ledger.check(self.root)

    def test_shared_requirement_cannot_cover_another_record(self):
        self.change('requirements', lambda doc: doc['entry'].pop(1))
        self.change('original-bugs', lambda doc: doc['entry'][1].update(links=['REQ-0001']))
        with self.assertRaisesRegex(ValueError, 'not reciprocal'):
            ledger.check(self.root)

    def test_json_rejects_duplicate_keys(self):
        path = self.root / 'docs/research/ledger/original-bugs.json'
        path.write_text(path.read_text(encoding='utf-8').replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            ledger.check(self.root)

    def test_invalid_json_and_root(self):
        path = self.root / 'docs/research/ledger/original-bugs.json'
        for text in ('{', '[]', 'null'):
            with self.subTest(text=text):
                path.write_text(text, encoding='utf-8')
                with self.assertRaises(ValueError):
                    ledger.check(self.root)

    def test_json_rejects_nonfinite_constants(self):
        path = self.root / 'docs/research/ledger/original-bugs.json'
        original = path.read_text(encoding='utf-8')
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value):
                path.write_text(original.replace('"schema_version": 1,', f'"schema_version": 1, "extra": {value},', 1), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'invalid JSON numeric constant'):
                    ledger.check(self.root)


if __name__ == '__main__':
    unittest.main()
