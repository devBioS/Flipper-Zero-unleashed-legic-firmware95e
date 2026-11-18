#!/usr/bin/env python3
"""Verify staged pack hashes inside an updater .tgz (use the FBT Python)."""
import argparse
import hashlib
import io
import json
import struct
import tarfile
from pathlib import Path
import heatshrink2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--inventory', type=Path, default=Path('build/legic-packs/files.json'))
    args = parser.parse_args()
    with tarfile.open(args.package) as update:
        files = {Path(m.name).name: m for m in update.getmembers() if m.isfile()}
        assert {'firmware.dfu', 'updater.bin', 'radio.bin', 'update.fuf', 'resources.ths'} <= files.keys()
        compressed = update.extractfile(files['resources.ths']).read()
        magic, version, window, lookahead = struct.unpack('<IBBB', compressed[:7])
        assert (magic, version) == (0x53445348, 1)
        raw = heatshrink2.decompress(compressed[7:], window_sz2=window, lookahead_sz2=lookahead)
    inventory = json.loads(args.inventory.read_text())
    with tarfile.open(fileobj=io.BytesIO(raw)) as resources:
        members = {m.name.lstrip('./'): m for m in resources.getmembers() if m.isfile()}
        for item in inventory:
            data = resources.extractfile(members[item['path']]).read()
            assert hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
        assert 'apps/NFC/nfc.fap' in members, 'Built NFC application missing'
        nfc = resources.extractfile(members['apps/NFC/nfc.fap']).read()
        protocols = ['iso14443_3a', 'iso14443_3b', 'iso14443_4a', 'iso14443_4b',
                     'iso15693_3', 'felica', 'mf_ultralight', 'mf_classic', 'mf_plus',
                     'mf_desfire', 'slix', 'st25tb', 'ntag4xx', 'type_4_tag', 'emv',
                     'texkom', 'legic_prime']
        for protocol in protocols:
            assert ('nfc_' + protocol + '.fal').encode() in nfc, protocol
        assert any(name.endswith('/cli_nfc.fal') for name in members), 'NFC CLI missing'
    print(f'PASS: {len(inventory)} base/extra files byte-identical; NFC application, CLI and all 17 protocol plugin filenames included')
    print('SHA256', hashlib.sha256(args.package.read_bytes()).hexdigest(), args.package)


if __name__ == '__main__':
    main()
