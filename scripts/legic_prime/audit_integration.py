#!/usr/bin/env python3
"""Compare the integrated NFC/API registrations against the exact Unleashed 095 tag."""
import csv
import io
import re
import subprocess
from pathlib import Path

BASE = '9c6327764c18fc8376b5941aa8bde79fe681fe8f'


def baseline(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], text=True)


def main():
    path = 'targets/f7/api_symbols.csv'
    def exports(text):
        return {r[2]: r for r in csv.reader(io.StringIO(text))
                if len(r) > 2 and r[0] in ('Function', 'Variable') and r[1] == '+'}
    old, new = exports(baseline(path)), exports(Path(path).read_text())
    assert all(new.get(k) == v for k, v in old.items()), 'Existing API export changed'
    print(f'PASS: {len(old)} original API exports retained; {len(new.keys() - old.keys())} added')
    for path in ['lib/nfc/protocols/nfc_device_defs.c', 'lib/nfc/protocols/nfc_poller_defs.c',
                 'lib/nfc/protocols/nfc_listener_defs.c',
                 'applications/main/nfc/helpers/protocol_support/nfc_protocol_support.c']:
        entries = re.findall(r'^\s*\[NfcProtocol\w+\].*', baseline(path), re.M)
        assert all(entry in Path(path).read_text() for entry in entries), path
        print('PASS: original registrations retained:', path)
    for path, prefix in [('lib/nfc/protocols/nfc_protocol.h', 'NfcProtocol'),
                         ('lib/nfc/nfc.h', 'NfcTech'),
                         ('targets/furi_hal_include/furi_hal_nfc.h', 'FuriHalNfcTech')]:
        def entries(text):
            return re.findall(r'^\s*(' + prefix + r'\w+),', text, re.M)
        old = [x for x in entries(baseline(path)) if x not in (prefix + 'Num', prefix + 'Invalid')]
        assert entries(Path(path).read_text())[:len(old)] == old, path
        print('PASS: original numeric enum IDs retained:', path)
    path = 'applications/debug/unit_tests/tests/nfc/nfc_test.c'
    def tests(text):
        return set(re.findall(r'MU_TEST\((\w+)\)', text))
    assert tests(baseline(path)) <= tests(Path(path).read_text())
    print('PASS: original NFC tests retained')


if __name__ == '__main__':
    main()
