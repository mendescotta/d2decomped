#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the JSON research ledger and render its bounded inventory (Python 3.9+)."""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys

REGISTRIES = ('requirements', 'original-bugs', 'deviations', 'missing', 'unverified', 'regressions')
SOURCES = ('bugs', 'deviations', 'todo', 'stubs', 'unverified')
STATUSES = {'unknown', 'documented', 'reported-fixed', 'reported-open', 'retracted', 'traced'}
MIRRORED = ('title', 'subsystem', 'original_behavior', 'port_behavior', 'status', 'confidence',
            'owner', 'last_verified_commit', 'evidence', 'tests')


def unique_object(pairs):
    """JSON duplicate keys are invalid, including metadata and nested records."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def invalid_constant(value):
    """The JSON format excludes NaN and infinities accepted by json's defaults."""
    raise ValueError(f'invalid JSON numeric constant: {value}')


def source_rows(root):
    """Return table identities and exact cells; escaped Markdown pipes stay in cells."""
    result = {}
    for name in SOURCES:
        section = 'Preamble'
        headers = None
        for line in (root / 'docs/research/re' / f'{name}.md').read_text(encoding='utf-8').splitlines():
            if line.startswith('#'):
                section = line.lstrip('# ').strip()
                headers = None
            if not line.startswith('|'):
                continue
            cells = [cell.strip().replace(r'\|', '|') for cell in re.split(r'(?<!\\)\|', line.strip('|'))]
            if all(re.fullmatch(r':?-+:?', cell) for cell in cells):
                continue
            if cells[0] in {'#', 'What', 'Address'}:
                headers = cells
                continue
            if headers is None or len(headers) != len(cells):
                raise ValueError(f'{name}: malformed table row: {line}')
            key = f'{name}:{section}:{cells[0]}'
            if key in result:
                raise ValueError(f'duplicate source identity: {key}')
            result[key] = dict(zip(headers, cells))
    return result


def fingerprint(cells):
    return hashlib.sha256(repr(sorted(cells.items())).encode()).hexdigest()


def check(root):
    records = {}
    counts = Counter()
    for name in REGISTRIES:
        doc = json.loads((root / 'docs/research/ledger' / f'{name}.json').read_text(encoding='utf-8'),
                         object_pairs_hook=unique_object, parse_constant=invalid_constant)
        if not isinstance(doc, dict):
            raise ValueError(f'{name}: registry must be a JSON object')
        if type(doc.get('schema_version')) is not int or doc['schema_version'] != 1:
            raise ValueError(f'{name}: unsupported schema_version')
        commit = doc.get('indexed_at_commit')
        if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError(f'{name}: indexed_at_commit requires a full commit')
        imported = doc.get('imported_on')
        if not isinstance(imported, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', imported):
            raise ValueError(f'{name}: imported_on requires YYYY-MM-DD')
        try:
            date.fromisoformat(imported)
        except ValueError as error:
            raise ValueError(f'{name}: invalid imported_on date') from error
        if not isinstance(doc.get('provenance'), str) or not doc['provenance'].strip():
            raise ValueError(f'{name}: provenance must be a nonempty string')
        if not isinstance(doc.get('entry'), list):
            raise ValueError(f'{name}: entry must be an array of objects')
        for row in doc['entry']:
            if not isinstance(row, dict):
                raise ValueError(f'{name}: entry must contain objects')
            identity = row.get('id')
            if not isinstance(identity, str) or not re.fullmatch(r'[A-Z]+-[0-9]+', identity) or identity in records:
                raise ValueError(f'{name}: invalid/duplicate id: {identity}')
            for field in ('title', 'subsystem', 'original_behavior', 'port_behavior', 'status', 'confidence', 'owner', 'last_verified_commit', 'evidence', 'tests', 'links', 'aliases'):
                if field not in row:
                    raise ValueError(f'{identity}: missing {field}')
            for field in ('title', 'subsystem', 'original_behavior', 'port_behavior', 'status', 'confidence', 'owner', 'last_verified_commit'):
                if not isinstance(row[field], str) or not row[field]:
                    raise ValueError(f'{identity}: {field} must be a nonempty string')
            for field in ('evidence', 'tests', 'links', 'aliases'):
                if not isinstance(row[field], list) or any(not isinstance(item, str) or not item for item in row[field]):
                    raise ValueError(f'{identity}: {field} must be a string array')
            if row['status'] not in STATUSES or not row['evidence']:
                raise ValueError(f'{identity}: invalid status or empty evidence')
            if row['last_verified_commit'] != 'unknown' and not re.fullmatch(r'[0-9a-f]{40}', row['last_verified_commit']):
                raise ValueError(f'{identity}: verification requires a full commit')
            if row['confidence'] not in {'unknown', 'documented', 'review-reported'}:
                raise ValueError(f'{identity}: invalid confidence')
            records[identity] = (name, row)
            counts[name] += 1
    aliases = set()
    covered = {}
    current = source_rows(root)
    for identity, (name, row) in records.items():
        for alias in row['aliases']:
            if alias in aliases or alias in records:
                raise ValueError(f'{identity}: duplicate alias: {alias}')
            aliases.add(alias)
        for target in row['links']:
            if target not in records:
                raise ValueError(f'{identity}: dangling link: {target}')
        for ref in row['evidence'] + row['tests']:
            if ref.startswith('https://'):
                continue
            path = ref.split('#', 1)[0]
            if not path or not (root / path).resolve().is_relative_to(root.resolve()) or not (root / path).is_file():
                raise ValueError(f'{identity}: missing or unsafe reference: {ref}')
        if name == 'requirements':
            if len(row['links']) != 1 or records[row['links'][0]][0] == 'requirements':
                raise ValueError(f'{identity}: requirement needs one registry link')
            if identity not in records[row['links'][0]][1]['links']:
                raise ValueError(f'{identity}: link is not reciprocal')
            linked = records[row['links'][0]][1]
            for field in MIRRORED:
                if row[field] != linked[field]:
                    raise ValueError(f'{identity}: mirrored {field} differs from {linked["id"]}')
            continue
        key = row.get('source_key')
        if key:
            if key in covered or key not in current:
                raise ValueError(f'{identity}: duplicate or removed source row: {key}')
            if row.get('source_sha256') != fingerprint(current[key]):
                raise ValueError(f'{identity}: source row changed; reconcile ledger: {key}')
            cells = current[key]
            if row.get('source_columns') != list(cells) or row.get('source_cells') != list(cells.values()):
                raise ValueError(f'{identity}: retained source cells differ from source')
            covered[key] = identity
        requirements = [target for target in row['links'] if records[target][0] == 'requirements']
        if len(requirements) != 1:
            raise ValueError(f'{identity}: needs exactly one requirement link')
        if records[requirements[0]][1]['links'] != [identity]:
            raise ValueError(f'{identity}: requirement link is not reciprocal')
    missing = current.keys() - covered.keys()
    if missing:
        raise ValueError('unmapped source rows: ' + ', '.join(sorted(missing)))
    return records, counts


def summary(records, counts):
    lines = ['# Ledger inventory', '', 'Generated by `python3 tools/ledger.py --summary`. Counts are indexed records,',
             'not unique behaviors or a game-completion denominator. Requirements mirror',
             'registry entries; overlapping source lists are retained.', '', '| Registry | Entries |', '|---|---:|']
    lines += [f'| {name} | {counts[name]} |' for name in REGISTRIES]
    lines += ['', '| Recorded status | Registry entries (excluding requirements) |', '|---|---:|']
    statuses = Counter(row['status'] for name, row in records.values() if name != 'requirements')
    lines += [f'| {status} | {count} |' for status, count in sorted(statuses.items())]
    lines += ['', 'A reported fix is audit history, not a freshly verified result. Unknown tests,',
              'owners and last-verified commits remain explicit. Original stubs are indexed',
              'under missing with their original kind; they are not port omissions.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='validate schema, references, source coverage and generated summary')
    parser.add_argument('--summary', action='store_true', help='print the generated inventory')
    parser.add_argument('--write-summary', action='store_true', help='replace docs/research/ledger/SUMMARY.md after validation')
    args = parser.parse_args()
    try:
        records, counts = check(args.root)
        output = summary(records, counts)
        destination = args.root / 'docs/research/ledger/SUMMARY.md'
        if args.write_summary:
            destination.write_text(output, encoding='utf-8')
        if args.check and destination.read_text(encoding='utf-8') != output:
            raise ValueError('SUMMARY.md is stale; run --write-summary')
        if args.summary:
            print(output, end='')
        else:
            print(f'ledger: {len(records)} records checked')
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f'ledger: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
