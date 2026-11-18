#!/usr/bin/env python3
"""Build and run actual PRNG/CRC/bit_lib sources with host assertions."""
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='legic-vectors-') as folder:
    tmp = Path(folder)
    (tmp / 'core').mkdir()
    # The bit library uses no RTOS facilities; only its check macros need a host adapter.
    (tmp / 'core/check.h').write_text('#include <assert.h>\n#include <stdlib.h>\n#define furi_crash(...) abort()\n#define furi_check(x, ...) assert(x)\n#define furi_assert(x) assert(x)\n')
    source = root / 'lib/nfc/protocols/legic_prime'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                    '-I' + str(tmp), '-I' + str(root), '-I' + str(root / 'lib'),
                    str(Path(__file__).with_suffix('.c')), str(source / 'legic_prime_prng.c'),
                    str(source / 'legic_prime_crc.c'), str(root / 'lib/bit_lib/bit_lib.c'),
                    '-o', str(tmp / 'vectors')], check=True)
    subprocess.run([str(tmp / 'vectors')], check=True)
