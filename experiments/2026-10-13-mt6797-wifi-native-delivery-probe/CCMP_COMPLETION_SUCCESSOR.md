# CCMP completion successor: C5 diagnosis and terminal-only observation

Status: one successor trial consumed, 2026-10-17. The owner explicitly resumed implementation
from `598040b5`, with device tests available after candidate validation and
owner-operated physical boot selection. This chat remains independent of
other agents and does not modify their shared checkout or assume device
custody from historical records. The [C6 result](CCMP6_RESULT.md) records DHCP,
a pending-disable failure and verified return; no unchanged retry is selected.

See [C6 preparation](CCMP6_PREPARATION.md) for the real pins and tooling review.

## Reproduced evidence and decision

The [comparison](results/ccmp-completion-comparison.json) was reproduced from
all three complete retained logs, checking their exact byte sizes, SHA-256
digests and contiguous record sequences. The
[extractor](analyze-ccmp-completion.py) emits only fixed numeric fields; it
neither prints nor republishes raw lines, paths, addresses or packet bytes.
Reproduce with Python 3.11+ and the three private `kmsg.log` files in C3/C4/C5
order. A mismatched input refuses without printing its contents.

| Question | Evidence | Decision or remaining limit |
| --- | --- | --- |
| Why did C5 stop? | Record 2041 at 140326541 us reports PID 6 data-TX timeout, elapsed 760 ms, debt 0 and credits 6. Record 2042 follows 1427 us later with -110, first 0, branch 1. | The in-flight 750 ms frame deadline was exceeded before the next guard. This is not a branch-2 guard/transport error or branch-4 length refusal. |
| Was the overall join deadline reached? | Data began at 138714183 us with 6144 ms data budget and 5000 ms teardown margin. In the pinned source the join deadline is data deadline plus that margin. | It cannot explain a stop only 1613785 us after data start. No deadline extension is justified. |
| Did pages prove TX completion? | Record 2040 returns the second three-page debit at 139590433 us. No PID 6 TX-done occurs anywhere in the 2057 records. | Returned pages and a recognized TX-done are different predicates. Firmware generation, delivery and host loss remain indistinguishable. |
| Was a completion rejected by the narrow TX-done matcher? | That path fails with -71 on branch 5. C5 stops at -110 on branch 1; C3/C4 stop at -71 on branch 4. | The terminal narrow rejection path is excluded for these runs. Unrecognized or undelivered records are not thereby excluded. |
| Did 0195 improve completion timing? | PID 5 submit-to-handled-completion is 1243 us in C3, 1431 us in C4 and 419973 us in C5. PID 6 completes in C3/C4, not C5. | These are host log intervals across different boots, not RF/firmware latency or proof of 0195 causality. PID 6 submit time was not logged and is not reconstructed. |
| Was the earlier gap-48 fixed? | C3/C4 reached post-CLOSED mismatches 76/28 and 449/401. C5 had no CLOSED receive or length refusal before its earlier stop. | The comparison point was not reached. No fixed/mismatch-free verdict follows. |

The prepared C5 driver was independently verified against the published
[source pins](RUNTIME_NO_POST_PROPOSAL.md): MAC `fdc2d7fb`, HIF `904ee916`,
header `55cea740`; full hashes remain in that record and the test runner.
Branch 1 contains the frame-deadline check; branch 2 is assigned immediately
before `mt6797_mac_join_guard`. The logged timeout predicate therefore
corrects the earlier broad description of a "guard timeout". The existing
combined stop predicate can also contain other simultaneous conditions;
the retained log does not enumerate every condition true at that tick.

## Separate length-contract review

The actual C5 HIF retains one pre-WRPLR acquisition for each requested port,
stages the complete selected length plus the existing extra-word span, and
requires selected/header equality before type publication or caller copy.
MAC requests port 0 then port 1 with fresh whole-word acquisitions. 0195 omits
only the successful MAC post acquisition; boot drain still uses its original
post metadata. No group stripping precedes the equality check.

An independent public download of the
[MT6797 register table, part 1](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_1.pdf)
on 2026-10-17 matched SHA-256
`e8ef503a32a8bb318a000fe6727d2bcdaa3557992a0ffed344e9de37acc2caff`.
Pages 1405-1406 describe next-packet lengths for each queue; pages 1426-1427
describe firmware length-queue submission and host consumption. This is a
documentary queue contract, not a measured AP-bridge latch/pop mechanism.
It supplies no justified aggregate-length decoder or 48-byte exception.
Whether repeated whole-word acquisitions disturb pairing remains unresolved.
No binary analysis or new device read was performed for this review.

## Selected smallest successor

[0196](../../patches/proposals/0196-wifi-mt6797-retain-terminal-ccmp-completion-observations.patch)
adds a MAC-only, terminal-only diagnostic to the existing opt-in stable-CCMP
epoch. It selects no repair. The concrete missing evidence is what the
existing guard and per-port receive calls returned during the failed epoch.

- Cache WHCR/WHISR only after an existing successful join reconciliation,
  with its return timestamp. This is the last successful acquisition, not a
  fault-time snapshot or a new read of consuming interrupt state.
- Retain each port's attempt/success/type-7 counts, opposite-half-nonzero
  count, and last result/pre-valid/pre-WRPLR/return timestamp. An opposite
  advertisement is neither a dropped packet nor a certified completion.
- Retain the last ordinary TX's PID and post-send return-time boundary from
  the existing frame-deadline assignment. Report the current deadline and
  in-flight state; do not infer the firmware submission/arrival time.
- Emit exactly three bounded lines once, at fail-stop before withdrawal or
  at healthy stage-3 cleanup. Emit nothing additional during ACTIVE.
  No packet bytes, peers, keys, PN bytes or network identifiers are retained.

Only `mac.c` changes. HIF/boot/scan implementation and all receive acceptance,
poison/no-copy, timers, budgets, key/PN gates and lifecycle rules are unchanged.
The observation is compiled under the existing default-off CCMP option and
armed only by the existing opted-in data phase. Its host bookkeeping and
terminal output can affect timing; a successful trial alone cannot prove
that the original problem disappeared.

Profile `mt6797-a53-wifi-ccmp-completion-observe` selects exact C5 ordered
690 patches plus 0196, with identical 26 fragments. The new named series is
a canonical-order subsequence. Existing explicit profile selections remain
unchanged; this profile is not the clean-board acceptance milestone.

## Validation and build boundary

The [actual-helper test](tests/run-ccmp-completion-observation-test.py) pins
the C5 source, checks every other driver/boot file unchanged and reverses the
exact MAC patch to its parent. Its C fixture compiles the actual helpers under
ASan/UBSan and checks default-off behavior, both ports, empty/opposite work,
accepted control/data, length/transport failure, invalid metadata clearing,
terminal-only three-line output and frozen state after reporting.

Run with the exact C5 and 0196-child source trees. Reuse the existing
`runtime-no-post-test.py` for the unchanged C4/C5 HIF comparison. These tests
verify host code, not hardware length-pop, crypto enforcement or completion.

Initial validation on 2026-10-17: the actual-helper ASan/UBSan test passed
locally and on Linux. The C4/C5 runtime-no-post comparison passed on Linux:
10 successes, 1638 common failure cases and exactly two omitted transport
operations on runtime success. Strict checkpatch reports one missing truthful
DCO sign-off, zero warnings/checks; the internal proposal deliberately carries
no invented sign-off and is not submission-ready. Local repository checks
passed, including all 29 profiles. Kernel compile/package/device validation
was still pending at that initial checkpoint; subsequent identities and the
consumed trial are linked above.

Before building: inspect the exact staged paths/diff, run repository checks
and profile audit, commit only Wi-Fi changes, verify the origin URL, push
clean intended inputs and use the standard Buildbox backend with 32 jobs.
Keep the restored September research outside this implementation commit.
Validate the complete package and built source identities before composition.
No deployment or package result is implied by this preparation document.

## One-trial hypothesis, observation and decisions

Hypothesis: the existing acquisition results distinguish missing advertised
control work, unserviced opposite-port work, or a receive/control-mode change
from a recognized-completion handling failure. The unique measurement is
terminal history from existing operations, not another unchanged C5 run.

Compose a fresh receipt-bound candidate from the validated successor package
and unchanged private parent/RAM/config/DT. Derive fresh prepare/install/
capture/session bindings through the existing tools; do not edit frozen C5
receipts or reuse them as successor deployment evidence. Verify live Gemian,
custody, power, GPT and boot2 guards before installation and full readback.
Shut down; the owner selects boot2 physically. Run one capture and one
session under inherited all-RX 512/1 MiB/delivery 64/wall 10 s-or-lower,
grant/deadline, key, PN and teardown limits; preserve/seal/quiesce and perform
one reviewed return. No additional register access, packet acceptance, retry
or radio mode is admitted by this diagnostic.

1. **Completion timeout recurs:** classify it using cached acquisition age,
   port attempts/results and TX identity. Do not equate empty selected halves,
   opposite advertisements or type-7 counts with a hardware producer cause.
2. **Length mismatch recurs:** retain the existing refusal and terminal port
   history. No shorter read, prefix copy, subtraction or recovery retry.
3. **Healthy network and cleanup:** require real DHCP, three real ping
   replies, fresh authenticated boot-bound SSH/ACK and stage-3 cleanup under
   the inherited finite protocol. Record bounded compatibility only.
4. **Other failure or missing history:** preserve it separately and stop at
   the actual evidence gap. Do not repeat the artifact to fill missing data.

Every branch returns through the reviewed recovery after preserving evidence;
historical recovery identities are not fresh live checks. Ordinary-mode
per-frame security, GTK/rekey/retirement, healthy reuse and clean-profile
ten-minute acceptance remain subsequent work, gated on this result.
