# Experiment: mainline I2C6 firmware-writer attestation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-18-mainline-i2c6-firmware-writer-attestation` |
| Status | `planned` |
| Subsystem | MT6797 SCP, Device-APC, and I2C6 ownership |
| Device variant | Planet Gemini PDA, MT6797 named development unit |
| Date(s) | 2026-08-18 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 6 blocker B1 |

## Question or hypothesis

Immediately before the proven stopped-DVFSP handoff could authorize I2C6, is
SCP still held inert while the exact ATF I2C6 Device-APC policy remains stable?

## Provenance and environment

- Runtime-proven parent: `da921x-lk-clock-readonly-provider`.
- New profile: `da921x-i2c6-firmware-writer-attestation`.
- Planned release: `7.1.3-gemini-i2c6-fwatt`.
- Canonical source delta: patch `0286`.
- Exact retained LK, ATF, SCP, and TEE images remain private evidence; only
  sanitized register contracts and derived observations are recorded here.
- Builds are permitted only through Buildbox from an exact clean pushed
  commit. No native VM build is permitted for this experiment.

## Safety assessment

The discriminator is read-only. It samples two SCP registers and bounded
Device-APC words, performs no I2C transfer of its own, and faults the existing
I2C6 access controller closed on every unexpected result. The profile keeps
the Linux SCP/remotproc drivers disabled, the DT SCP node disabled, DA921x
register-data writes at zero, and CPU8/CPU9 excluded.

Candidate construction performs no device access. A later validated candidate
may use the standing live-GPT `boot2` workflow with full readback and clean
shutdown; no new partition backup is required under the project recovery
policy.

## Associated code

- [`DESIGN.md`](DESIGN.md) defines the attribution and fail-closed boundary.
- [`contract.json`](contract.json) fixes every address, sample, pass condition,
  forbidden action, and decision branch.
- Canonical patch:
  `patches/v7.1.3/0286-soc-mediatek-attest-I2C6-firmware-writer-closure.patch`.
- Isolated fragment:
  `configs/gemini-i2c6-firmware-writer-attestation.fragment`.
- [`scripts/build-attestation-dtb.sh`](scripts/build-attestation-dtb.sh)
  derives the exact DT from the proven provider DT and adds only the two named
  read-only register windows.
- `scripts/validate.py` validates the source/profile/contract boundary and
  representative unsafe mutations.

## Procedure

1. Validate the patch, profile, fragment, contract, DT derivation, and unsafe
   mutations against the exact prepared source.
2. Commit and push a clean source boundary, then build only the attestation
   profile on Buildbox and fetch only its validated package.
3. Construct and independently validate one checksum-pinned Android-v0
   candidate using the exact derived attestation DT.
4. Install only to live-GPT logical `boot2`, require full-partition readback,
   and shut the device down cleanly.
5. Boot `boot2` once and capture `firmware_writer_attestation` before any
   follow-up action. Return natively to Gemian after the bounded capture.

## Observations

Pending source validation, Buildbox build, candidate validation, and one device
attempt.

## Analysis

Pending. A pass closes only the SCP-writer branch when combined with the
exact-image audit and the existing stopped-PCM runtime evidence. A failure is
still useful because the raw samples distinguish nonzero SCP state from an
unstable or unexpected Device-APC policy.

## Conclusion

`planned`. Gate-6 writing and CPU8/CPU9 admission remain closed.

## Follow-up

On a pass, proceed to Gate-6 blocker B2: prove the native MT6797 I2C controller
can issue exactly one two-byte message without enabling any DA921x write path.
On a failure, keep B1 open and design the next read-only discriminator from the
captured raw register state.
