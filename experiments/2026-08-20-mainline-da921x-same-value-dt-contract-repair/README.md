# DA921x same-value DT contract repair

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-da921x-same-value-dt-contract-repair` |
| Status | `running` |
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
the legacy client field and the supplier counters; continuation uses the same
still-idle boot.

## Analysis

This is a DT-only contract correction. A different runtime outcome is
attributable to the restored supplier resources; kernel code and configuration
are unchanged.

## Conclusion

The DT-only candidate is independently validated, deployed, and runtime-proven
through the exact idle 20-entry pretrigger state. The single physical token is
still unused; a corrected same-boot continuation is pending.

## Follow-up

If the repaired boot still lacks the client, retain supplier/I2C6 lifecycle and
dmesg evidence and stop before the token. If the pretrigger gates pass, consume
the one token and classify the exact 32-entry terminal ledger.
