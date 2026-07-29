# DA921x legacy driver lifecycle

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-29-da921x-legacy-lifecycle` |
| Status | `attempt 1 failed before recoverable serviceability; Gate 3 open` |
| Subsystem | regulator, I2C, arm64 Device Tree |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-07-29 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 |

## Question or hypothesis

Can the dedicated legacy DA921x identification driver match the fixed
`0x68`/`0x69` tuple, bind, unbind without a transaction, and bind again while
preserving the known-good serviceability baseline and issuing no register-data
write?

This experiment changes Gate 2 only by adding a read-only controller-level
message-shape oracle. The oracle has no transfer trigger and cannot alter
controller programming. CPUs 8 and 9 remain offline and no regulator provider
or consumer exists.

## Provenance and environment

- Kernel: pinned Linux 7.1.3 from `kernel/manifest.json`
- Profile: `da921x-legacy-lifecycle`
- Gate 2 inputs: canonical patches `0123` through `0125`
- Gate 3 observation patch: canonical patch `0126`
- Configuration, patchset, package, candidate, and toolchain identities:
  `results/offline-validation.json`
- Boot path: owner-selected logical `boot2`

## Safety assessment

The driver has no register-data write helper, regmap, provider, IRQ, PM,
shutdown, or remove callback. Its successful probe is exactly fourteen
combined one-byte-pointer/one-byte-read transfers. Unbind has no driver
callback and must leave all controller counters unchanged. Rebind may add
exactly another fourteen combined pointer reads.

The controller oracle only classifies messages already submitted to I2C6 and
exposes atomic counters in the existing read-only handoff status. It adds no
debugfs trigger, writable sysfs file, retry, reset, transfer, or hardware
programming path.

Installation may target only live-GPT-resolved logical `boot2` in the known-good
OS. The installer must reject an active, mounted, read-only, wrong-sized, or
unexpected target; record the predecessor checksum; pad to the exact partition
size; write once; sync and flush; and require matching complete readback.
Recovery relies on the verified project-wide device backup captured at project
start. After a successful verified write, shut down cleanly so the owner can
select `boot2`; never reboot or select a slot automatically.

Stop on any package, candidate, predecessor, power, target, readback,
serviceability, tuple, lifecycle, counter, CPU-state, I2C5/AP-DMA, console,
keyboard, USB, or native-reboot gate failure. Do not repeat an identical
artifact unless a new independent observation is defined first.

## Associated code

- `scripts/validate-static.py`: manifest, patch, configuration, and
  observation-surface contract
- `scripts/build-lifecycle-dtb.sh`: deterministic Gauss serviceability-DT
  derivative with only the exact legacy tuple and I2C6 pin contract
- `scripts/build-candidate.sh`: storage-inert, duplicate DT/container assembly
  with standard package and LK-container validation
- `scripts/collect-runtime.sh`: fail-closed, exact-identity one-shot
  bind/unbind/rebind collector
- `scripts/validate-runtime.py`: independent exact decision-table classifier
- `scripts/test-runtime-validator.py`: positive and fail-closed classifier
  self-tests
- `scripts/derive-installer.py`: source-pinned derivation of the proven guarded
  Gauss installer, calibrated from the final candidate and requiring the exact
  Gauss full-partition predecessor
- `results/pre-boot-hypothesis.txt`: machine-readable decision table

## Procedure

1. Validate the Gate 2 static contract and the new controller oracle.
2. Audit every manifest profile against canonical patch order.
3. Build the exact lifecycle profile twice in independent out-of-tree build
   directories and require byte-identical boot-bearing outputs.
4. Assemble the Android-v0 LK candidate twice from the same pinned
   serviceability initramfs and require byte-identical candidates.
5. Validate the kernel, DT, configuration, initramfs, container, and absence
   of regulator/A72 consumers or writable observation controls.
6. Install only to live-resolved logical `boot2` under the guarded policy.
   Do not reboot automatically.
7. After an owner-attended `boot2` selection, require the exact kernel and USB
   identities, CPUs 0--7 online, CPUs 8--9 offline, and the established
   console, keyboard, USB, I2C5/AP-DMA, DVFSP, and reboot baseline.
8. Record the initial successful driver bind and require oracle counters
   `14` total, `8` primary, `6` page2, and zero for every write/other class.
9. Unbind once and require every I2C6 counter to remain unchanged.
10. Rebind once and require the exact identity log plus counters `28` total,
    `16` primary, `12` page2, and zero for every write/other class.
11. Preserve the first result and apply the predeclared decision table.

## Pre-boot hypothesis, evidence, and decisions

| Result | Unique attributable evidence | Next action |
| --- | --- | --- |
| Initial bind, zero-transaction unbind, and exact rebind all pass with the serviceability baseline unchanged | Exact lifecycle driver log plus independent I2C6 oracle transitions `14 -> 14 -> 28`, with `8/6 -> 8/6 -> 16/12` address counts and every write/other counter zero | Close Gate 3 and permit design of the resource-only provider gate; still do not enable writes or CPUs 8--9 |
| Tuple mismatch | Driver returns the fixed transcript mismatch and does not bind; oracle gives the attempted strict-prefix count | Stop at chip/board identification; reconcile the changed tuple |
| Transfer or lifecycle failure | Driver/core error plus an oracle count inconsistent with the expected phase | Keep the issue in the I2C/driver layer; do not add a provider |
| Any register-data write, write-only message, other transfer shape, or other address | Nonzero independent oracle counter | Stop immediately; reject the candidate and investigate the unexpected transaction |
| Any serviceability regression | Candidate-attributed baseline failure with exact package and boot identities | Block provider work and investigate without repeating the same artifact |

No outcome establishes a regulator provider, writable operation, resume
ownership, voltage or enable state, or Cortex-A72 support.

## Observations

The static contract, canonical manifest-series audit, ShellCheck, deterministic
DT derivation, and runtime-classifier self-tests pass. Two independent
out-of-tree builds from the same prepared source produced byte-identical
boot-bearing outputs, all DTBs, and normalized provenance. Two independent
candidate assemblies produced byte-identical boot containers, padded boot2
images, DTs, and serviceability initramfses. The selected candidate and
calibrated installer were exported under the Git-ignored artifacts root and the
exported candidate manifest passes.

The named Gemini initially did not answer two read-only SSH reachability
probes. Once it was available in Gemian, the calibrated installer resolved
logical `boot2` to `/dev/mmcblk0p30`, confirmed root remained
`/dev/mmcblk0p29`, and required the exact installed Gauss full-partition hash.
It preserved and verified the complete predecessor backup, wrote only
`boot2`, synced and flushed it, and required both remote and local complete
readbacks to equal the selected padded candidate. The private evidence
manifest passes. The installer itself did not reboot or shut down. See
`results/install-boot2-20260729.txt`.

After installation, the owner changed the standing policy to rely on the
verified project-wide recovery backup rather than create a fresh partition
backup for each boot2 write, and to shut down after every successful verified
boot2 write. The installed boot2 checksum was verified once more, the device
was shut down cleanly without rebooting, SSH closed from the remote side, and a
follow-up reachability check timed out. See
`results/post-install-shutdown-20260729.txt`.

On attempt 1, the owner selected `boot2`, observed a grey screen, and then an
automatic reboot. No recoverable candidate console or USB service appeared.
The returned Gemian instance had a boot ID different from the pre-attempt
instance and reported boot reason 4, `androidboot.bootreason=wdt_by_pass_pwk`,
and `powerup_reason=reboot`. These independently corroborate a watchdog-block
class return but do not identify the reset source.

Pstore was present but empty. `/proc/last_kmsg` contained only the same generic
74-byte ram-console header seen after earlier pre-serviceability returns
(`hw_status: 5`, FIQ step 0), with no candidate kernel, initramfs, lifecycle, or
watchdog-handoff marker. A post-return live-GPT resolution and full read-only
checksum confirmed that `boot2` still contains the exact installed candidate
and that the Gemian boot ID stayed stable during collection. See
`results/runtime-candidate-gate3-attempt-1-20260729.txt`.

## Analysis

Offline evidence establishes reproducible compilation and candidate assembly,
not hardware behavior. The guarded installation passed every target, power,
predecessor, backup, write, flush, and readback gate, but still establishes no
runtime behavior.

Attempt 1 takes the predeclared serviceability-regression branch. The grey
screen and automatic return are attributable to the exact installed candidate
and physical `boot2` selection, while the recovered reset tokens establish
only a nondiscriminating watchdog-block class. Empty pstore and the generic
ram-console header do not establish whether the candidate kernel entered or
which stage failed.

Because the lifecycle collector never became reachable, this attempt provides
no driver bind, tuple, unbind, rebind, I2C6-oracle, or zero-write result. It
cannot close Gate 3 and does not permit provider work. Repeating the identical
artifact is forbidden because it would add no independent decision-changing
observation.

## Conclusion

Gate 3 remains open after attempt 1 failed before recoverable serviceability.
No driver-lifecycle, regulator-provider, or Cortex-A72 conclusion is made.

## Follow-up

Investigate the pre-serviceability regression offline and define a durable
independent observation path or a justified candidate delta before another
device boot. Do not boot the identical artifact again.

Only a later serviceable lifecycle result may advance to Roadmap Gate 4
ownership/rollback evidence and Gate 5 resource-only provider registration.
