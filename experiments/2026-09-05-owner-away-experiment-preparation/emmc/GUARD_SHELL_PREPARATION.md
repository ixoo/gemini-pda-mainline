# eMMC logger guard exact-shell preparation

Status: host and exact BusyBox fixtures passed; the assigned execution is
recorded in [GUARD_SHELL_RESULTS.md](GUARD_SHELL_RESULTS.md). The protocol below
was prepared before that one execution. Collection and completion drafts remain disabled,
with runtime facts unset. This item changes no candidate, first-baseline
protocol, physical admission or target action budget.

## Published source boundary

[`guarded_observation.py`](guarded_observation.py) is an inert generator: no
import-time reads, CLI, transport or execution. Its caller supplies the genuine
pinned collector-generated baseline bytes. It validates phases, complete
hashes, read UUID, bounded baseline bytes and a bounded safe release token.
[`test-guard-shell.py`](test-guard-shell.py) adds a fixed, hardware-free fixture
using five existing pinned sources: collector, session generator, eMMC bounded
runner/classifier and historical observer. Source pins are checked before
imports and before a passing result.

| Source | SHA-256 |
| --- | --- |
| `guarded_observation.py` | `5fe4472b3ed61812cc05b6662decac89f6799d81de06def4f8bae51cb920317d` |
| `test-guard-shell.py` | `eb02e660f779c34fe4b0c75beccd79ce5a621211b522166022c7bbf24cc5f284` |

Before refactoring the private launcher, its original guard and pre/read/post
programs were compared byte for byte with the inert generator, using the
genuine collector body. Independent review repeated this comparison by
isolating the original two functions. Both passed. The original private
launcher source digest was
`bfc584591c3bdf1cdfd51a6c39f397bff8481c028a08945cbd645f8ff526395d`.
Those comparisons used synthetic candidate identities, not runtime evidence.

## Exact claim and limits

The pinned BusyBox shell evaluates the real guard prefix against confined
fixture paths. Full original pre/post programs receive syntax checks; exact
`guard + genuine baseline body` composition is then checked before that one
body boundary is replaced by a fixed sentinel. Read composition checks the
entire exec suffix and arguments and permits only a hash-checked observer
sentinel. Receipts retain original program and genuine baseline-tail hashes.

Positive cases require the six ordered guard applets, exactly one body entry,
exact output, zero status and empty stderr. Each guard refusal requires nonzero
status, no body marker and no observer output. Hostile proxy calls refuse under
optimized Python. Ordinary fixture hash, PID-file and stat applets use exact
BusyBox/QEMU in exact mode; process entries and candidate hashes are synthetic.

This tests guard-before-body and exact dispatch. It executes neither the
baseline target body nor the real eMMC observer. Existing body and launcher
orchestration receipts remain separate. No device node, storage read, logger,
mount, reboot or SSH action is available through the proxy. A live logger
precondition does not establish process continuity or the final complete log.
Trailing PID newlines are accepted by shell command substitution; the
ten-digit positive uses a virtual fixture process, not a real PID claim.

## Finite cases, bounds and host review

The fixed `EXPECTED_CASES` inventory contains 52 cases:

- One constructor refusal group and five positive compositions/PID boundaries.
- Six hash failures/mismatches across BusyBox, observer and logger helper.
- Six terminal-marker and eight log/PID-file type/path refusals.
- One PID-read failure, eleven malformed PID strings and three executable
  stat/identity failures.
- Five runner controls: stdout/stderr caps, timeout, timely SIGTERM and a
  deterministic late-SIGTERM refusal.
- Six hostile proxy calls: applet, live device/proc/sys path, arbitrary shell
  command and an escaping symlink.

Each case has one absolute 90-second ceiling including syntax, execution,
process-group and directory cleanup. The case suite has a 600-second ceiling.
Child allowances are recomputed with a one-second cleanup reserve. Deadline
and signal controls use at most five seconds in exact mode, two in host mode.
Each child has 128 KiB stdout and 16 KiB stderr caps; per-case retained files
are at most 2 MiB and removed on handled success/failure.

Review corrected timeout reuse across syntax/execution and a self-signal race.
The outer signal handler now remains installed until the sole sender joins;
late delivery cannot count as timely interruption. Case accounting includes
temporary-directory cleanup. Independent proxy review found no further
actionable confinement issue. All 52 cases passed in normal and optimized
host Python (20.105 and 20.005 seconds). These host receipts have null
BusyBox/QEMU identities and establish no exact ARM64 result.
All 52 cases passed again in both modes at their tracked repository paths
(20.062 and 20.138 seconds). The common repository gate passed all 189
profiles; its Linux-only provenance fixture was skipped on macOS. No kernel
build, DT/schema or device check was needed or run for this source extraction.

Target policy remains one 16 MiB read attempt, 20-second observer deadline,
40-second outer read ceiling, no retry and independent final log/recovery.

## Retained public artifact and bounded transfer proposal

The required ARM64 BusyBox is 1,914,704 bytes, SHA-256
`52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`.
It came from the pinned public Ubuntu `busybox-static_1.36.1-6ubuntu3.1_arm64.deb`
at `ports.ubuntu.com`, package digest
`d96535e0402c011e0ee43449799df2f4504d44b842e4f2b3a6cbc845508eaafc`.
The retained local public package still matches that digest. Existing
[`build-userspace.sh`](../baseline/scripts/build-userspace.sh) records the
public URL and both pins; the retained userspace package contains its license.

One authorized read-only Buildbox cache/artifact inventory returned a bounded
refusal and no usable inventory. Remote absence is therefore unproven. There
was no source/build mutation or download. The fallback was verified locally:
the existing reviewed `parse_newc` reader, digest
`19c1c63df5f4732d3cae253a5b7edbb90d0ad609ed1ea411a200dc0060adba9c`,
read the historical pre-authentication initramfs, digest
`344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b`.
Only `bin/busybox` was materialized, with expected regular-file metadata,
length and digest. The managed temporary extraction was removed afterward.
No candidate was reconstructed or retested.

The proposed transfer window permits only those exact redistributable binary
bytes if a retained remote copy is unavailable. Re-extract just that member
under an ignored managed temporary root; install cleanup immediately. Stream
at most 1,914,705 bytes into a new private remote staging file under the managed
userspace root, with a 30-second transfer ceiling. Refuse anything other than
the exact 1,914,704-byte length and digest before making it executable. Do not
transfer an initramfs, candidate, source tree, credential or authentication
material. Remove both temporary binary copies and fixture state on success
or failure after retaining the bounded sanitized receipt. Reuse an existing
validated remote binary without deleting that retained input if supplied.

## One proposed exact invocation

Orchestrator must assign the shared-backend window and concrete managed paths.
Git-fetch this published source revision into the managed userspace checkout;
require its exact commit and clean state. Use the shared Buildbox lock and the
userspace dispatch lock with immediate refusal when busy. No compile runs.
Canonical QEMU must have digest
`4f55e2e88dc05dc0f619562d5795b8eb25ed2ad2547504fb4835207a6911c350`;
the fixture checks both executable digests before and after its suite.

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/emmc/test-guard-shell.py --work-root MANAGED_ROOT --busybox RETAINED_BUSYBOX --qemu CANONICAL_QEMU
```

The three placeholders are reviewed local artifact paths on Buildbox, never
device endpoints. Wrap this single invocation in a 660-second process limit
with five-second forced cleanup and a managed-state cleanup trap. Bound the
returned receipt to 32 KiB stdout and 16 KiB stderr. The fixture's internal
600-second suite and per-child limits remain stricter.

Require zero exit and empty stderr, with exactly one JSON object containing
classification `emmc-guard-shell-fixtures-pass`, mode `exact-busybox-qemu`,
`case_count: 52`, the complete ordered case inventory, exact source/executable
hashes, 90/600-second budgets and one-second cleanup. It must also record
`device_access: false`, `target_bodies_executed: false` and claim
`guard-before-fixed-body-and-exact-dispatch-only`. A failure, wrong identity,
partial receipt or exhausted budget does not pass. Preserve diagnostics and
review before any retry. Exact execution now has its linked receipt; physical
readiness remains separate and pending.
