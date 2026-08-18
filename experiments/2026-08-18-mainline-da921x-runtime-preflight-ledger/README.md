# Experiment: mainline DA921x runtime-triggered read-only preflight

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-18-mainline-da921x-runtime-preflight-ledger` |
| Status | `running` (candidate live; corrected attempt `1e` pending) |
| Subsystem | MT6797 I2C6 transfer attribution and DA921x Gate-6 preflight |
| Device variant | Planet Gemini PDA, MT6797 named development unit |
| Date(s) | 2026-08-18 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 blockers B3 and B4 |

## Question or hypothesis

Can the exact Gate-5 boot reach the established USB shell while retaining the
first 20 I2C6 transfers, then complete the ten reviewed read-only preflight
transfers only after a checksum-pinned host capture and one exact trigger?

This separates boot serviceability and prior-transfer attribution from the ten
automatic reads that preceded the stopped predecessor's observation failure.

## Provenance and environment

- Runtime-proven parent: `da921x-lk-clock-readonly-provider`, release
  `7.1.3-gemini-da921x-lkro`.
- Stopped predecessor:
  [automatic preflight attempt](../2026-08-17-mainline-da921x-readonly-preflight-ledger/results/runtime-attempt-1-no-mainline-usb-20260818.txt).
- New profile: `da921x-runtime-preflight-ledger`.
- Planned release: `7.1.3-gemini-da921x-preflight-rt`.
- Canonical source delta: patch `0285` after bounded ledger patch `0283` and
  automatic-preflight implementation patch `0284`.
- Builds are permitted only through Buildbox from an exact clean pushed commit.

## Safety assessment

The source remains read-only at the hardware boundary. The runtime option is
mutually exclusive with automatic preflight, checks the exact provider and
`2/4/0` phase state before its first transfer, accepts one exact token, and has
no retry or reset. Invalid, repeated, or precondition-failing requests perform
zero I2C operations.

The ten accepted transfers use the existing combined one-byte-pointer/one-byte
read path. There is no register-data write, writable provider operation,
`PAGE_CON` access, consumer, firmware-owner claim, or CPU request. CPU8 and CPU9
remain excluded with `maxcpus=8`. Candidate construction performed no device
access or hardware write; deployment remains governed by the live-GPT `boot2`
installer and its full-readback/shutdown gates.

## Associated code

- [`DESIGN.md`](DESIGN.md) fixes the state machine and two-stage observation.
- [`contract.json`](contract.json) fixes the 20-entry pre-trigger and 30-entry
  post-trigger sequences plus the immutable decision map.
- Canonical patch:
  `patches/v7.1.3/0285-regulator-trigger-legacy-DA921x-read-only-preflight.patch`.
- Isolated fragment:
  `configs/gemini-da921x-runtime-preflight-ledger.fragment`.
- [`scripts/validate.py`](scripts/validate.py) validates patch/profile/contract
  structure and rejects representative unsafe mutations.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh) and
  [`scripts/test-candidate.py`](scripts/test-candidate.py) assemble and
  independently validate the exact Android-v0 candidate.
- [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh) persists the exact
  pre-trigger capture before one non-retriable trigger attempt.
- [`results/prebuild-source-validation-20260818.txt`](results/prebuild-source-validation-20260818.txt)
  records the exact-source apply check, validators, and checkpatch boundary.
- [`results/buildbox-package-20260818.txt`](results/buildbox-package-20260818.txt),
  [`results/offline-candidate-validation-20260818.txt`](results/offline-candidate-validation-20260818.txt),
  and [`results/collector-prearm-validation-20260818.txt`](results/collector-prearm-validation-20260818.txt)
  freeze the build, candidate, and observation path.

Run from the repository root:

```sh
python3 experiments/2026-08-18-mainline-da921x-runtime-preflight-ledger/scripts/validate.py
./scripts/validate-manifest-series
```

## Procedure

1. Validate the exact patch, profile, fragment, contract, and unsafe mutations.
2. Commit and push a clean source boundary before requesting Buildbox.
3. Build only `da921x-runtime-preflight-ledger` through Buildbox and fetch only
   its validated package.
4. Construct and independently validate one checksum-pinned Android-v0
   candidate with the exact inherited serviceability DT and initramfs.
5. Use the guarded live-GPT installer for inactive `boot2`, full readback, and
   clean shutdown without a fresh backup.
6. Pre-arm a collector that retains an exact 20-entry capture before it can
   issue the one-shot token. Capture an exact 30-entry result or the immediate
   trigger-time transport boundary, then return natively to Gemian only after a
   complete pass.

## Observations

- Patch `0285` applies cleanly in a read-only dry run against Buildbox's exact
  prepared source. The source/profile/contract validator rejects eleven unsafe
  mutations; the historical predecessor validator and all 82 manifest-profile
  series invariants pass. Strict checkpatch reports zero checks, two expected
  quoted-status-string warnings, and the deliberately absent synthetic DCO
  sign-off. This experiment-only patch is not submission-ready.
- Buildbox compiled exact clean pushed commit `a3679cd38937bf9a7c9e25d19385e8f992506370`
  as release `7.1.3-gemini-da921x-preflight-rt`; package provenance and all
  packaged checksums passed. No native VM build ran.
- The independently reproduced candidate has raw SHA-256 `5f1ce652cee1fe77a4d963849dd047a9fbed6b0a25ef8fb48bcde74cb30b665d`
  and exact 16 MiB padded SHA-256
  `af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296`.
  All 32 LK gates and twelve negative DT mutations passed.
- The collector/classifier tests reject eleven unsafe runtime mutations and
  enforce a durable exact-20 capture, one trigger attempt, zero trigger retry,
  and native reboot only after an exact post-trigger pass.
- The installer resolved inactive logical `boot2` as `/dev/mmcblk0p30`, wrote
  and read back exact padded SHA-256 `af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296`,
  then confirmed the device unreachable after a clean shutdown. It made no new
  partition backup under the standing project recovery policy.
- Attempt 1 reached release `7.1.3-gemini-da921x-preflight-rt`, the direct USB
  shell, keyboard, DA921x I2C client, and CPUs 0--7 online with CPUs 8--9
  offline. Its pre-trigger probe stopped before the trigger because BusyBox
  `find` did not descend the symlinked I2C device directory.
- A bounded read-only diagnostic resolved the single client as
  `/sys/bus/i2c/devices/1-0068`, confirmed `readonly_preflight` readable and
  still `idle`, with zero attempts, zero preflight reads, and zero register-data
  writes. Attempt `1b` used the repaired direct resolver and captured the full
  idle state plus exact 20-entry ledger six times, but the interactive shell
  prompt prefixed the opening marker. The exact-line host gate correctly
  stopped before the trigger. Both probes now end the prompt line before their
  opening marker; checksum pins, syntax, ShellCheck, ordering, and eleven unsafe
  classifier mutations pass for continuation attempt `1c`. See
  [`results/runtime-attempt-1-observer-path-20260818.txt`](results/runtime-attempt-1-observer-path-20260818.txt)
  [`results/runtime-attempt-1b-observer-framing-20260818.txt`](results/runtime-attempt-1b-observer-framing-20260818.txt),
  and [`results/collector-attempt-1c-validation-20260818.txt`](results/collector-attempt-1c-validation-20260818.txt).
- Attempt `1c` produced an exactly framed, durable pre-trigger capture. The
  fail-closed classifier then exposed an incorrect offline inference in the
  frozen contract: registration entries 14--15 are repeatably `68:d7,68:d9`,
  not `68:5d,68:5e`; the following four observer entries remain
  `68:d7,68:5d,68:d9,68:5e`. All counts, message shapes, completions, and
  zero-write invariants passed. The corrected classifier accepts the retained
  capture and rejects the old entry-14 inference as an unsafe mutation. See
  [`results/runtime-attempt-1c-pretrigger-contract-correction-20260818.txt`](results/runtime-attempt-1c-pretrigger-contract-correction-20260818.txt)
  and [`results/collector-attempt-1d-validation-20260818.txt`](results/collector-attempt-1d-validation-20260818.txt).
- Attempt `1d` durably classified the corrected exact-20 pre-trigger ledger and
  issued one shell token command, but the initramfs's read-only sysfs mount
  rejected the redirection before the driver callback. The runtime state
  remained `idle` with zero attempts and zero preflight reads; the ledger stayed
  at 20 with zero writes, and no reboot occurred. The corrected probe now uses
  the repository's established trapped temporary writable virtual-sysfs window
  and requires read-only restoration. Its classifier rejects an un-restored
  mount among thirteen unsafe runtime mutations. See
  [`results/runtime-attempt-1d-readonly-sysfs-20260818.txt`](results/runtime-attempt-1d-readonly-sysfs-20260818.txt)
  and [`results/collector-attempt-1e-validation-20260818.txt`](results/collector-attempt-1e-validation-20260818.txt).

## Analysis

The pre-trigger capture is decision-changing even if the token causes an
immediate reset: it preserves the full 20-entry startup ledger and proves the
candidate reached the same serviceability boundary as Gate 5. A post-trigger
capture can then attribute the exact ten additional reads without conflating
them with boot success.

## Conclusion

The source, build, candidate, deployment, mainline serviceability, and repaired
collector boundaries are `confirmed`. The runtime-preflight hardware result
remains `inconclusive` because attempts `1` through `1d` stopped before the
driver accepted the token. Attempt `1c` confirmed the corrected exact
pre-trigger ledger, and attempt `1d` localized the remaining boundary to the
read-only sysfs mount. Gate-6 blockers B1--B4 and CPU8/9 admission remain
closed.

## Follow-up

Commit and push the trapped sysfs-mount window, then run exact continuation
attempt `1e` against the still-live candidate. Retain and classify the exact
20-entry pre-trigger ledger before the sole token attempt. The authoritative
ordered runtime and decision boundary remains [Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation).
