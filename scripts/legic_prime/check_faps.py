#!/usr/bin/env python3
"""Check ELF32 FAP manifests and both standard and fast-relocation imports."""
import argparse
import csv
import json
import struct
from pathlib import Path


def symhash(name):
    value = 5381
    for byte in name.encode():
        value = (value * 33 + byte) & 0xFFFFFFFF
    return value


def sections(data):
    assert data[:6] == b'\x7fELF\x01\x01', 'Expected little-endian ELF32'
    offset = struct.unpack_from('<I', data, 32)[0]
    size, count, names_index = struct.unpack_from('<HHH', data, 46)
    headers = [struct.unpack_from('<10I', data, offset + i * size) for i in range(count)]
    names = data[headers[names_index][4]:][:headers[names_index][5]]
    return [(names[h[0]:].split(b'\0', 1)[0].decode(), h,
             data[h[4]:h[4] + h[5]]) for h in headers]


def inspect(data, exports):
    table = sections(data)
    meta = next(d for n, _, d in table if n == '.fapmeta')
    magic, version, minor, major, target = struct.unpack_from('<IIHHH', meta)
    assert (magic, version, major, target) == (0x52474448, 1, 88, 7), 'Incompatible manifest'
    imports = set()
    for name, header, blob in table:
        if name.startswith('.fast.rel'):
            assert blob[0] == 1, 'Unsupported fast relocation format'
            count = struct.unpack_from('<I', blob, 1)[0]
            pos = 5
            for _ in range(count):
                internal = blob[pos] & 128
                value = struct.unpack_from('<I', blob, pos + 1)[0]
                pos += 5
                if internal:
                    pos += 4
                else:
                    imports.add(value)
                offsets = struct.unpack_from('<I', blob, pos)[0]
                pos += 4 + 3 * offsets
            assert pos == len(blob)
        elif header[1] == 2:  # SHT_SYMTAB
            strings = table[header[6]][2]
            for pos in range(0, len(blob), header[9]):
                index, _, _, info, _, section = struct.unpack_from('<IIIBBH', blob, pos)
                if index and section == 0 and info >> 4:
                    symbol = strings[index:].split(b'\0', 1)[0].decode()
                    imports.add(symhash(symbol))
    return {'api': f'{major}.{minor}', 'imports': len(imports),
            'missing_hashes': [f'{h:08x}' for h in sorted(imports - exports)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--api', type=Path, default=Path('targets/f7/api_symbols.csv'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    exports = {symhash(r[2]) for r in csv.reader(args.api.open())
               if len(r) > 2 and r[0] in ('Function', 'Variable') and r[1] == '+'}
    private_api = json.loads(Path(__file__).with_name('totp-private-api.json').read_text())
    totp_exports = {symhash(name) for name in private_api['symbols']}
    results = {}
    for path in sorted(args.root.rglob('*')):
        if path.suffix not in ('.fap', '.fal'):
            continue
        try:
            relative = str(path.relative_to(args.root))
            available = exports
            if relative.startswith('apps_data/totp/plugins/'):
                available = exports | totp_exports
            results[relative] = inspect(path.read_bytes(), available)
        except (AssertionError, ValueError, StopIteration, struct.error) as error:
            results[str(path.relative_to(args.root))] = {'error': str(error)}
    args.out.write_text(json.dumps(results, indent=2) + '\n')
    failures = {p: r for p, r in results.items() if r.get('error') or r.get('missing_hashes')}
    print(f'{len(results)} files checked; {len(failures)} require review. Report: {args.out}')
    for path, result in failures.items():
        print(path, result)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
