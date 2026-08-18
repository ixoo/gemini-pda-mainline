# Experiment: mainline DA921x read-only preflight ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-17-mainline-da921x-readonly-preflight-ledger` |
| Status | `running` (exact boot2 deployment verified; one runtime observation pending) |
| Subsystem | MT6797 I2C6 transfer attribution and DA921x Gate-6 preflight |
| Device variant | Planet Gemini PDA, MT6797 named development unit |
| Date(s) | 2026-08-17 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 blockers B3 and B4 |

## Question or hypothesis

Do the two unexplained Gate-5 transfers come from one regulator-core enable
query for each read-only provider, and does the exact serviceable mainline path
have a stable, unlocked, disabled-Buck-B prestate for the reviewed same-value
no-op?

One runtime can answer both questions without performing a register-data write:
the I2C6 ledger must contain the exact 30-entry sequence in
[`contract.json`](contract.json), while two preflight passes must agree on all
five full bytes and classify `V_LOCK` clear, `BUCKB_CONT = 0x00`, and both Buck
B selectors as `0x46`.

## Provenance and environment

- Parent profile: `da921x-lk-clock-readonly-provider`.
- New profile: `da921x-readonly-preflight-ledger`.
- Planned kernel release: `7.1.3-gemini-da921x-preflight`.
- Fixed parent runtime: [Gate-5 result](../2026-08-17-mainline-da921x-readonly-provider-baseline/results/runtime-attempt-1-success-20260817.txt).
- Design parent: [bounded no-op review](../2026-08-17-mainline-da921x-bounded-noop-write-review/README.md).
- Source patches: `0283` (controller ledger) and `0284` (provider preflight).
- Builds are permitted only through Buildbox after the exact commit is pushed.

## Safety assessment

The implemented source is read-only. It adds no transfer trigger, writable
provider operation, register-data write, consumer, retry, `PAGE_CON` access,
firmware-owner claim, CPU request, or DT change. The ledger records at most one
pointer byte per entry and fails visibly on overflow. The preflight reuses only
the already-proven combined pointer/read shape.

The exact candidate has passed Buildbox compilation, profile/config validation,
two deterministic container constructions, independent candidate validation,
and the complete inherited serviceability gates. CPU8 and CPU9 remain excluded
with `maxcpus=8`. The only permitted hardware action is the guarded write of
that checksum-pinned payload to live-GPT-resolved inactive `boot2`.

## Associated code

- [`DESIGN.md`](DESIGN.md) defines the observation and decision boundaries.
- [`contract.json`](contract.json) fixes the expected 30-entry sequence,
  preflight, aggregate counters, and decision map.
- [`scripts/validate.py`](scripts/validate.py) validates source, profile,
  checksums, patch syntax, and six unsafe mutations.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh) and
  [`scripts/test-candidate.py`](scripts/test-candidate.py) source-pin the exact
  package, inherited serviceability DT/initramfs, Android-v0 construction, and
  independent container/DT/configuration gates.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh) inherits live-GPT
  resolution, inactive/unmounted target checks, no-fresh-backup policy, full
  readback, and clean shutdown.
- [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh), its read-only
  [remote probe](scripts/remote-runtime-probe.sh), and the fail-closed
  [classifier](scripts/classify-runtime.py) bind one USB/netcat observation to
  the exact payload and immutable decision map. The
  [classifier test](scripts/test-runtime-classifier.py) rejects eight unsafe
  transfer, preflight, CPU, and identity mutations.
- [`results/buildbox-package-20260818.txt`](results/buildbox-package-20260818.txt),
  [`results/offline-candidate-validation-20260818.txt`](results/offline-candidate-validation-20260818.txt),
  and [`results/predeployment-hypothesis-20260818.txt`](results/predeployment-hypothesis-20260818.txt)
  freeze the exact package, candidate, and one-boot decision map.

Run from the repository root:

```sh
python3 experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/scripts/validate.py
./scripts/validate-manifest-series
```

## Procedure

1. Validate the two patches, exact-parent profile, fragment, contract, and
   representative unsafe mutations.
2. Commit and push the complete source boundary before requesting Buildbox.
3. Build only `da921x-readonly-preflight-ledger` on Buildbox and fetch only its
   validated package.
4. Construct and validate one exact boot candidate while preserving the
   Gate-5 initramfs, DT serviceability set, CPU closure, and recovery path.
5. Install only to live-GPT-resolved inactive `boot2`, verify the full readback,
   and shut the device down cleanly.
6. On one owner-selected boot, collect the ledger, preflight, provider,
   serviceability, CPU, and fault records before native reboot to Gemian.
7. Classify only against the immutable decision map and retain sanitized
   evidence.

## Observations

- Static source implementation is complete. The source/contract validator,
  six unsafe mutations, 81-profile series invariant, patch-hunk checks, and
  read-only applicability checks against Buildbox's exact prepared Linux tree
  pass. Checkpatch reports zero code checks for both patches; quoted-string
  warnings and the deliberately absent synthetic DCO sign-off remain recorded
  in the [prebuild receipt](results/prebuild-source-validation-20260817.txt).
- Buildbox built exact clean commit `f2837f05083b...` as
  `7.1.3-gemini-da921x-preflight`. Package checksums pass, the exact profile
  gates are present, and no native VM build ran.
- The package-built Gemini DT is byte-identical to the Gate-5 package DT. The
  final DT therefore reuses only the exact inherited serviceability derivation;
  the new attributable delta is the kernel/configuration that adds the bounded
  ledger and ten read-only preflight reads.
- Two independent Android-v0 constructions and two independent padding paths
  are byte-identical. All 32 LK/container gates pass, and the independent
  validator rejects twelve CPU-clock, ownership, provider, and serviceability
  mutations. The exact 16 MiB payload is
  `41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3`.
- No device access, boot2 write, regulator write, or CPU8/CPU9 request has
  occurred during candidate construction.
- Guarded deployment resolved live-GPT logical `boot2` as inactive, unmounted
  p30 while Gemian used p29. Stable external power, exact write, synchronization,
  flush, independent full readback, temporary-readback cleanup, and clean
  shutdown passed without a fresh backup or automatic reboot. The device is
  confirmed unreachable. See the
  [deployment receipt](results/deployment-1-20260818.txt).
- The checksum-pinned collector, read-only remote probe, and classifier pass
  syntax/source-identity checks. A complete synthetic 30-entry fixture passes;
  eight unsafe mutations are rejected. See the
  [collector pre-arm receipt](results/collector-prearm-validation-20260818.txt).

## Analysis

The phase counter makes the prior two-transfer explanation directly testable
instead of relying on a regulator-core inference. The controller ledger then
cross-checks the exact addresses and registers independently. Two complete
preflight passes add ten known reads, bringing the expected total to 30 while
remaining below the fixed 32-entry bound.

Even a complete pass cannot authorize a regulator write. It can close only
the transfer-attribution and live-preflight blockers; firmware-writer exclusion
and the native two-byte write shape remain separate gates.

## Conclusion

The offline candidate boundary is `confirmed`; the hardware conclusion remains
`inconclusive` pending one exact runtime observation. The raw Android-v0 image
is `4a0c440604ac4ebd82a1fa139020f02ae4d758cc9b89bc6509a782434d8e62e7`.
Nothing in this result opens a writable regulator or A72 boundary.

## Follow-up

Publish the deployment and pre-arm receipts, start the checksum-pinned
collector, and only then physically select `boot2` once. See
[Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation)
for the authoritative exit criteria.
