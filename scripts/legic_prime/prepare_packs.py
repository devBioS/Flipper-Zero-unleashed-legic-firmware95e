#!/usr/bin/env python3
"""Stage the release-095 base and extra packs into Unleashed's resource metapackage."""
import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]


def main():
    lock = json.loads((Path(__file__).with_name('packs.lock.json')).read_text())
    cache = ROOT / 'build/legic-packs'
    cache.mkdir(parents=True, exist_ok=True)
    resources = ROOT / 'applications/main/extra_resources/resources'
    inventory = []
    for pack, spec in lock.items():
        archive = cache / spec['name']
        if not archive.exists():
            urllib.request.urlretrieve(spec['url'], archive)
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == spec['sha256'], archive
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if member.isdir():
                    continue
                assert member.isfile(), member.name
                parts = PurePosixPath(member.name).parts
                assert len(parts) >= 3 and '..' not in parts and not member.name.startswith('/')
                assert parts[0] == pack + '_pack_build'
                if parts[1] == 'artifacts-' + pack:
                    relative = Path('apps', *parts[2:])
                else:
                    assert parts[1] == 'apps_data', member.name
                    relative = Path('apps_data', *parts[2:])
                data = tar.extractfile(member).read()
                dest = resources / relative
                if dest.exists() and dest.read_bytes() != data:
                    raise RuntimeError(f'Refusing to overwrite different resource: {dest}')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                inventory.append({'pack': pack, 'path': str(relative),
                                  'sha256': hashlib.sha256(data).hexdigest()})
    (cache / 'files.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(f'Staged {len(inventory)} files; inventory: {cache / "files.json"}')


if __name__ == '__main__':
    main()
