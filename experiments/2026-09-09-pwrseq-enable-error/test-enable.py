#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the actual enable function with injected callbacks, without hardware."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='prepared Linux source directory')
parser.add_argument('--expect-bug', action='store_true')
args = parser.parse_args()
source = (args.source / 'drivers/power/sequencing/core.c').read_text()
start = source.index('int pwrseq_enable(struct pwrseq_desc *desc)')
end = source.index('EXPORT_SYMBOL_GPL(pwrseq_enable);', start)
function = source[start:end]
prefix = r'''
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#define might_sleep() ((void)0)
#define guard(kind) (void)
#define scoped_guard(kind, lock) if (1)
struct pwrseq_device { int rw_lock, state_lock, dev; };
struct pwrseq_unit { int unused; };
struct pwrseq_target {
 struct pwrseq_unit *unit;
 int (*post_enable)(struct pwrseq_device *);
};
struct pwrseq_desc {
 struct pwrseq_device *pwrseq;
 struct pwrseq_target *target;
 bool powered_on;
};
static int unit_result, post_result, enables, posts, disables;
static int device_is_registered(int *dev) { return *dev; }
static int pwrseq_unit_enable(struct pwrseq_device *p, struct pwrseq_unit *u)
{ (void)p; (void)u; enables++; return unit_result; }
static int pwrseq_unit_disable(struct pwrseq_device *p, struct pwrseq_unit *u)
{ (void)p; (void)u; disables++; return 0; }
static int post(struct pwrseq_device *p)
{ (void)p; posts++; return post_result; }
'''
suffix = r'''
int main(void)
{
 /* unit result, post result, callback, registered, already on, expected return,
    expected enabled flag, enable calls, post calls, disable calls */
 const int cases[][10] = {
  {-EIO, 0, 1, 1, 0, -EIO, 0, 1, 0, 0},
  {-EIO, -EINVAL, 1, 1, 0, -EIO, 0, 1, 0, 0},
  {-EIO, 0, 0, 1, 0, -EIO, 0, 1, 0, 0},
  {0, 0, 1, 1, 0, 0, 1, 1, 1, 0},
  {0, -EINVAL, 1, 1, 0, -EINVAL, 0, 1, 1, 1},
  {0, 0, 0, 1, 0, 0, 1, 1, 0, 0},
  {0, 0, 1, 0, 0, -ENODEV, 0, 0, 0, 0},
  {0, 0, 1, 1, 1, 0, 1, 0, 0, 0},
 };
 int failed = 0;
 for (unsigned int i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
  const int *c = cases[i];
  struct pwrseq_device p = {.dev = c[3]};
  struct pwrseq_unit u = {0};
  struct pwrseq_target t = {.unit = &u, .post_enable = c[2] ? post : NULL};
  struct pwrseq_desc d = {.pwrseq = &p, .target = &t, .powered_on = c[4]};
  unit_result = c[0]; post_result = c[1]; enables = posts = disables = 0;
  int ret = pwrseq_enable(&d);
  if (ret != c[5] || d.powered_on != c[6] || enables != c[7] ||
      posts != c[8] || disables != c[9]) {
   printf("case %u failed: ret=%d powered=%d calls=%d/%d/%d\n",
          i, ret, d.powered_on, enables, posts, disables);
   failed++;
  }
 }
 if (pwrseq_enable(NULL)) failed++;
 printf("cases=9 failed=%d\n", failed);
 return failed;
}
'''
with tempfile.TemporaryDirectory(prefix='pwrseq-enable-test-') as tmp:
    cfile = Path(tmp) / 'test.c'
    executable = Path(tmp) / 'test'
    cfile.write_text(prefix + function + suffix)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    str(cfile), '-o', str(executable)], check=True)
    result = subprocess.run([str(executable)], check=False)
    expected = 2 if args.expect_bug else 0
    if result.returncode != expected:
        raise SystemExit(f'expected {expected} failing cases, got {result.returncode}')
