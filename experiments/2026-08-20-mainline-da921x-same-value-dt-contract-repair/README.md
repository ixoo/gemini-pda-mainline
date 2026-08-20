# DA921x same-value DT contract repair

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-da921x-same-value-dt-contract-repair` |
| Status | `completed` runtime success; closed to repetition |
| Subsystem | MT6797 DVFSP handoff, I2C6, DA921x |
| Device variant | Gemini PDA, named project device |
| Date(s) | 2026-08-20 |

## Question or hypothesis

The first same-value-write candidate stopped before issuing its token because no
DA921x I2C client existed. The candidate combined a kernel configured for the
firmware-writer attestation/transaction-window contract with the older handoff
DT node containing only the CSPM register window. The hypothesis is that
restoring the already runtime-proven three-window handoff DT, without changing
the kernel, ramdisk, or LK contract, restores the I2C6 child and permits the
single bounded same-value-write attempt.

## Provenance and environment

- Kernel commit: `7c012d736f78898be08bfd8430a25c8708a62e1d`
- Kernel release: `7.1.3-gemini-da921x-same-write`
- Profile: `da921x-same-value-write`
- Configuration SHA-256: `61590965540ad27624b64c8906a58f87d36ed15821e769f5ec93871f39695614`
- Correct DT SHA-256: `80972fc24406d5be8818c891d06fb8ed4d40f2332bd1eda2d8263597029ea683`
- Boot path: live-GPT logical `boot2`, only while inactive and unmounted

## Safety assessment

CPU8/CPU9 admission remains closed. The retained production kernel permits one
exact write of `0xda 0x46` to DA921x register `0x46`, only after its existing
pretrigger and ledger gates pass. There is no automatic retry, inverse write,
consumer request, CPU request, or PAGE_CON access. Installation uses the
guarded logical-`boot2` workflow, verifies the full-partition readback, and
shuts the device down. Recovery relies on the project-wide backup captured at
project start; no fresh partition backup is required.

## Root-cause localization

The rejected candidate DT (`d7dba05e...`) had no `reg-names` property and only
`<0 0x11015000 0 0x1000>` in `reg`. Patch 0286 maps `scp-cfg` and `devapc-ao`
by name and returns from probe when either is absent. The I2C6 handoff consumer
then defers, so `regulator@68` is never instantiated. This exactly predicts the
six observed `da921x_i2c_client_count=0` pretrigger probes. It does not test or
implicate the regulator same-value-write implementation.

The repaired DT adds the already proven named windows:

`reg-names = "cspm", "scp-cfg", "devapc-ao"`

`reg = <0 0x11015000 0 0x1000 0 0x100a0000 0 0x1000 0 0x1000e000 0 0x1000>`

## Procedure

1. Reassemble the same kernel and serviceability ramdisk with the repaired DT.
2. Independently validate package identity, LK layout, DT resource contract,
   the exact same-value gates, and negative DT mutations.
3. Install the padded image to live-GPT logical `boot2`, verify full readback,
   and shut down.
4. On one physical `boot2` selection, retain lifecycle/pretrigger evidence
   before issuing the single token. Capture a terminal classification and
   return to Gemian only after the result is durable.

## Observations

The predecessor attempt is recorded in
`../2026-08-19-mainline-da921x-same-value-write-implementation/results/runtime-attempt-1-pretrigger-mismatch-20260820.txt`.

Offline assembly produced raw image `87b38fc4...` and exact 16 MiB boot2
image `85dbd8d0...`. All 32 LK gates passed. The original eight DT mutations
and three new handoff-resource mutations were rejected.

The first two normal transfers and one extended-liveness transfer stopped
before the device write gate because Gemian's SSH stream became unresponsive.
The successful attempt sent only the raw 6,895,616-byte prefix and sparsely
extended the staging file to 16 MiB. The unchanged remote gate verified the
full staged SHA-256 before writing. Live GPT resolved `boot2` to p30 and the
active root to p29; power was present at 100% with Good health. The full write,
flush, post gate, independent 16 MiB readback, and clean shutdown all passed.

The first selected boot proved the DT repair: the three named windows were
present, the handoff became ready after late validation, I2C6 bound, one
DA921x client and the same-value attribute existed, and the exact 20-entry
idle ledger was retained with zero writes. The token remained withheld because
the new lifecycle probe renamed a classifier field and both inherited
same-value probes omitted the supplier transaction-window attribute. This is a
collector contract error, not a candidate failure. The probes now retain both
the legacy client field and the supplier counters.

The corrected continuation on that same still-idle boot passed every
pretrigger gate and issued the exact token once. The driver completed its 12
bounded actions and reached `state=passed`, `attempts=1`, `last_error=0`. The
sole write was ledger entry 25, a completed one-message transfer to address
`0x68` with payload `[0xda, 0x46]`. Five preflight bytes were
`7b,c1,00,46,46`; immediate and delayed target readback were both `46`; and
the four poststate bytes were `7b,c1,00,46`. The final ledger was exactly
32/32 with no overflow, foreign address, reset failure, retry, second write,
consumer request, CPU request, or `PAGE_CON` access. CPUs 0--7 remained online
and CPUs 8--9 remained offline.

The inherited classifier initially rejected `oracle_other_transfers=1` while
expecting zero. The pinned lifecycle-oracle source increments that counter for
every transfer not shaped as a combined pointer read, including the sole
write, independently of the write-only and register-data counters. A
source-pinned one-line classifier correction therefore expects the value to
equal the write count. The immutable capture then classifies
`success-same-value-write`; its updated regression suite passes the pretrigger,
success, and both terminal failure fixtures and rejects 14 unsafe mutations.
This correction changes no device observation.

After the corrected result and checksums were durable, one native USB-shell
reboot returned to changed-identity Gemian. The returned live GPT still
resolved boot2 as p30 and root as p29, the full boot2 checksum remained
`85dbd8d0...`, pstore was empty, and external power remained present at 100%
with Good battery health. The reported `wdt_by_pass_pwk` reason is retained as
a nondiscriminating return class, not attributed to the regulator action.

## Analysis

This is a DT-only contract correction. The restored supplier resources explain
the client/bind difference while kernel code and configuration remain
unchanged. The terminal ledger independently attributes the one physical
register-data write and every surrounding read. The stable full-byte prestate,
same-value payload, immediate/delayed target readback, and unchanged full-byte
poststate establish the reviewed no-op write/readback contract; they do not
establish an active rail transition, writable consumer, resume behavior, or
CPU8/CPU9 readiness.

## Conclusion

The DT-only candidate is independently validated, deployed, and runtime-proven
through the exact one-token terminal result. The physical same-value write
passed once with exact payload attribution and stable readback while all rail
and A72 requests remained closed. Preserve the result and do not repeat the
candidate or token.

## Follow-up

Advance to Roadmap Gate 7 by reconciling the already retained external-provider,
SPM/SRAM, clock, CCI, PSCI, safe-off, and recovery evidence into one production
CPU8 admission contract. CPU9 remains closed. No further same-value write or
identical boot is required.
