# Experiment: mainline DA921x read-only preflight ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-17-mainline-da921x-readonly-preflight-ledger` |
| Status | `running` (source implemented; Buildbox and hardware not yet run) |
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

The candidate is not yet built or eligible for boot2. Before a device boot, it
must pass Buildbox compilation, exact profile/config validation, candidate and
container checks, and the complete inherited serviceability gates. CPU8 and
CPU9 remain excluded with `maxcpus=8`.

## Associated code

- [`DESIGN.md`](DESIGN.md) defines the observation and decision boundaries.
- [`contract.json`](contract.json) fixes the expected 30-entry sequence,
  preflight, aggregate counters, and decision map.
- [`scripts/validate.py`](scripts/validate.py) validates source, profile,
  checksums, patch syntax, and six unsafe mutations.

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
- No kernel build, candidate construction, device access, or hardware action
  has occurred in this experiment yet.

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

`inconclusive` pending Buildbox and one exact runtime observation. The source
contract is implemented without opening a writable or A72 boundary.

## Follow-up

See [Roadmap Gate 6](../../docs/ROADMAP.md#6-prove-one-bounded-writable-operation)
for the authoritative ordered follow-up and exit criteria.
