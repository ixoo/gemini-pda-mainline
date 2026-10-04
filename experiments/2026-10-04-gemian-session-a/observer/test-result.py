#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile and test the actual observer acceptance predicate without hardware."""
import hashlib
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
TEST = r"""
#include <assert.h>
#include "gemini-reg06-observer.h"

int main(void)
{
    struct gemini_reg06_record good = {
        .result = 2, .master_calls = 1, .transfers = 1, .irq = 1,
        .fifo_count = 1, .controller_ok = true, .fifo_path = true,
        .wrrd = true, .fifo_seen = true, .value = 0
    };
    struct gemini_reg06_record r;
    int count, ret;

    /* A legitimate zero byte must remain publishable. */
    assert(gemini_reg06_valid(&good));
    good.value = 0xff;
    assert(gemini_reg06_valid(&good));
    /* All short/overlong FIFO counts, even with success, are rejected. */
    for (count = 0; count < 16; count++) {
        r = good; r.fifo_count = count;
        assert(gemini_reg06_valid(&r) == (count == 1));
    }
    /* Negative errors and partial message counts cannot publish a byte. */
    for (ret = -121; ret <= 3; ret++) {
        r = good; r.result = ret;
        assert(gemini_reg06_valid(&r) == (ret == 2));
    }
    for (count = 0; count < 8; count++) {
        r = good; r.irq = count;
        assert(gemini_reg06_valid(&r) == (count == 1));
    }
    r = good; r.master_calls = 0; assert(!gemini_reg06_valid(&r));
    r = good; r.master_calls = 2; assert(!gemini_reg06_valid(&r));
    r = good; r.transfers = 0; assert(!gemini_reg06_valid(&r));
    r = good; r.transfers = 2; assert(!gemini_reg06_valid(&r));
    r = good; r.controller_ok = false; assert(!gemini_reg06_valid(&r));
    r = good; r.fifo_path = false; assert(!gemini_reg06_valid(&r));
    r = good; r.wrrd = false; assert(!gemini_reg06_valid(&r));
    r = good; r.fifo_seen = false; assert(!gemini_reg06_valid(&r));
    return 0;
}
"""

with tempfile.TemporaryDirectory(prefix='gemini-reg06-result-') as tmp:
    root = Path(tmp)
    (root / 'linux').mkdir()
    (root / 'linux/types.h').write_text(
        '#include <stdbool.h>\n#include <stdint.h>\n'
        'typedef uint8_t u8; typedef uint16_t u16;\n')
    (root / 'test.c').write_text(TEST)
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(root), '-I' + str(HERE), str(root / 'test.c'),
                    '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
print('acceptance_cases=159 result=pass')
print('header_sha256=' + hashlib.sha256(
    (HERE / 'gemini-reg06-observer.h').read_bytes()).hexdigest())
print('not_tested=kernel-integration,locking,sysfs,physical-transport')
