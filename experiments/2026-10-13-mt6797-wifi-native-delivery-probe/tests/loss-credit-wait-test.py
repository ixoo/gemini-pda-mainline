#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual installed-source waiter with a deterministic worker interleave."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path)
a=p.parse_args()
raw=a.source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='20a29c7a54d6eddd52d15a9e8c2fdfde4f455743a06cf111e2812e472ada8d82'
source=raw.decode()
start=source.index('static int mt6797_mac_join_wait_credit(struct mt6797_mac *mac)\n{')
end=source.index('\n}\n',start)+3
function=source[start:end]
prelude=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
typedef uint64_t u64;
struct mt6797_mac { u64 join_credit_deadline; int mutex,join_credit_done;
 int first_error; bool closing,join_retired,join_running,join_credit_pending; };
static struct mt6797_mac *current;
static bool next_command;
static u64 ktime_get_ns(void) { return 1; }
static unsigned long nsecs_to_jiffies(u64 n) { return n; }
static void mutex_unlock(int *m) { (void)m; }
static void mutex_lock(int *m) { (void)m; }
static void wait_for_completion_timeout(int *c,unsigned long t) {
 (void)c; (void)t;
 /* Worker credits the waiter's command, completes it, then can submit
  * the next cleanup command before returning the shared MAC mutex. */
 current->join_credit_pending=false;
 if(next_command) current->join_credit_pending=true;
}
'''
main=r'''
int main(void) {
 struct mt6797_mac m={.join_credit_deadline=100,.join_running=true,
                      .join_credit_pending=true};
 current=&m;
 assert(mt6797_mac_join_wait_credit(&m)==0);
 m.join_credit_pending=true; next_command=true;
 assert(mt6797_mac_join_wait_credit(&m)==-ETIMEDOUT);
 assert(ktime_get_ns()<m.join_credit_deadline);
 m.first_error=-EPROTO;
 assert(mt6797_mac_join_wait_credit(&m)==-EPROTO);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    (root/'fixture.c').write_text(prelude+function+main)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(root/'fixture.c'),'-o',str(root/'fixture')],check=True)
    subprocess.run([str(root/'fixture')],check=True)
print('actual-source waiter: earlier credit succeeds; next-command pending reproduces premature -110; poison preserved')
