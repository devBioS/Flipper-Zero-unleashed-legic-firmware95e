#!/usr/bin/env python3
"""Build and validate the complete Unleashed 095e + LEGIC Prime release."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUFFIX = 'unlshd-095e-legic'
BASE = '9c6327764c18fc8376b5941aa8bde79fe681fe8f'
PR_BASE = '66613d2b46e4aa533aeaf8181d2a1e6566616a4e'
PR_HEAD = '9ef097609fbebd540e5286dfbbe751b4daad4422'


def run(*args, env=None):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('release-artifacts'))
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError('Release output must be empty; refusing to mix build results')
    if (ROOT / 'documentation/legic_prime').exists():
        raise RuntimeError('Private German integration reports must not be published')

    env = os.environ.copy()
    env.update(DIST_SUFFIX=SUFFIX, WORKFLOW_BRANCH_OR_TAG='legic-prime-095e',
               FORCE_NO_DIRTY='yes')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    env['SOURCE_DATE_EPOCH'] = subprocess.check_output(
        ['git', 'show', '-s', '--format=%ct', 'HEAD'], cwd=ROOT, text=True).strip()

    run('python3', 'scripts/legic_prime/audit_integration.py')
    run('python3', 'scripts/legic_prime/host_vectors.py')
    run('python3', 'scripts/legic_prime/prepare_packs.py')
    run('python3', 'scripts/legic_prime/check_faps.py',
        'applications/main/extra_resources/resources', '--out', output / 'fap-check.json')
    run('./fbt', 'COMPACT=1', 'DEBUG=0', 'updater_package', env=env)

    toolchain_root = Path(env.get('FBT_TOOLCHAIN_PATH', str(ROOT)))
    toolchain = toolchain_root / 'toolchain/current/bin'
    package = ROOT / f'dist/f7-C/flipper-z-f7-update-{SUFFIX}.tgz'
    sdk = ROOT / f'dist/f7-C/flipper-z-f7-sdk-{SUFFIX}.zip'
    run(toolchain / 'python3', 'scripts/legic_prime/verify_package.py', package)
    report = subprocess.check_output([
        'python3', str(ROOT / '.github/scripts/fw_size_report.py'),
        '--size-bin', str(toolchain / 'arm-none-eabi-size'),
        '--elf', str(ROOT / 'build/f7-firmware-C/firmware.elf'),
        '--dfu', str(ROOT / 'build/f7-firmware-C/firmware.dfu'),
        '--copro-bin', str(ROOT / 'lib/stm32wb_copro/firmware/stm32wb5x_BLE_Stack_light_fw.bin'),
        '--out', str(output / 'flash-report.md'),
    ], cwd=ROOT, text=True)
    flash = json.loads(report)
    if flash['usable_free_bytes'] < 0:
        raise RuntimeError('Firmware overlaps the radio/FUS region')
    (output / 'flash-report.json').write_text(json.dumps(flash, indent=2) + '\n')
    for source in (package, sdk):
        shutil.copy2(source, output / source.name)

    inventory = json.loads((ROOT / 'build/legic-packs/files.json').read_text())
    provenance = {
        'repository': env.get('GITHUB_REPOSITORY', 'local'),
        'commit': commit, 'unleashed_095_base': BASE,
        'legic_pr': 'https://github.com/flipperdevices/flipperzero-firmware/pull/4468',
        'legic_pr_base': PR_BASE, 'legic_pr_head': PR_HEAD,
        'variant': '095e (Base Apps + Extra Apps)', 'sdk_api': '88.27',
        'build_command': './fbt COMPACT=1 DEBUG=0 updater_package',
        'pack_lock': json.loads((ROOT / 'scripts/legic_prime/packs.lock.json').read_text()),
        'pack_file_count': len(inventory),
        'fap_count': sum(item['path'].endswith('.fap') for item in inventory),
        'fal_count': sum(item['path'].endswith('.fal') for item in inventory),
        'flash': flash,
    }
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    notes = f'''Unleashed 095e with LEGIC Prime, built from `{commit}`.

- Complete self-update package including the original 095 Base and Extra Apps.
- LEGIC Prime reading and emulation in the NFC app; writing through `nfc legic wrbl`.
- All original NFC registrations and public API exports are checked before building.
- Pack checksums, FAP imports, the embedded NFC plugins and the C2 flash boundary are checked.
- Available flash before the radio/FUS region: **{flash['usable_free_bytes']} bytes**.
- Original app packs: {provenance['fap_count']} FAPs and {provenance['fal_count']} FALs.

Download `flipper-z-f7-update-{SUFFIX}.tgz` for installation. The SDK ZIP is for developers.
Verify `SHA256SUMS` before use. Back up the complete SD card, including `.int` and
`apps_data`, and keep the original 095e update package for recovery.

User-reported hardware tests cover reading MIM256/MIM1024 tags, matching Proxmark
dumps and emulation at real readers. Writing to physical tags, MIM22 and the full
regression matrix have not been confirmed. CI runs host vectors and build/package
checks; it does not perform RF tests or install firmware on a device.
'''
    (output / 'RELEASE_NOTES.md').write_text(notes)
    sums = [hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name
            for path in sorted(output.iterdir()) if path.is_file()]
    (output / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    print(f'Validated release: {output}', flush=True)


if __name__ == '__main__':
    main()
