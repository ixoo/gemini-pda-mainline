# Experiment: mainline DA921x runtime-triggered read-only preflight

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-18-mainline-da921x-runtime-preflight-ledger` |
| Status | `running` (candidate validated; deployment pending) |
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
- No device access, partition write, runtime I2C operation, or CPU8/CPU9 request
  has occurred for this experiment yet.

## Analysis

The pre-trigger capture is decision-changing even if the token causes an
immediate reset: it preserves the full 20-entry startup ledger and proves the
candidate reached the same serviceability boundary as Gate 5. A post-trigger
capture can then attribute the exact ten additional reads without conflating
them with boot success.

## Conclusion

The source, build, candidate, and collector boundaries are `confirmed`; the
hardware result remains `inconclusive` pending one exact runtime. Gate-6
blockers B1--B4 and CPU8/9 admission remain closed.

## Follow-up

Deploy the exact candidate to inactive logical `boot2`, require full readback
and clean shutdown, then arm the collector before one physical boot selection.
The authoritative ordered runtime and decision boundary remains
[Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation).
