# Experiment: mainline I2C6 firmware-writer attestation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-18-mainline-i2c6-firmware-writer-attestation` |
| Status | `completed-failed-closed` |
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
- Built release: `7.1.3-gemini-i2c6-fwatt`.
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
- [`scripts/validate.py`](scripts/validate.py) validates the
  source/profile/contract boundary and
  representative unsafe mutations.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh) and
  [`scripts/test-candidate.py`](scripts/test-candidate.py) assemble and
  independently validate the exact Android-v0 candidate.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh) derives the guarded
  live-GPT installer for only this exact candidate.
- [`scripts/collect-runtime.sh`](scripts/collect-runtime.sh),
  [`scripts/remote-attestation-probe.sh`](scripts/remote-attestation-probe.sh),
  and [`scripts/classify-runtime.py`](scripts/classify-runtime.py) freeze the
  first-boot observation and both decision branches before deployment.
- [`results/prebuild-source-validation-20260818.txt`](results/prebuild-source-validation-20260818.txt),
  [`results/buildbox-package-20260818.txt`](results/buildbox-package-20260818.txt),
  and [`results/offline-candidate-validation-20260818.txt`](results/offline-candidate-validation-20260818.txt)
  record the exact source, package, and candidate boundaries.

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

- Patch `0286` applies cleanly against Buildbox's exact prepared source. The
  source/profile/contract validator rejects ten unsafe mutations and the
  canonical manifest-series audit passes all 83 profiles.
- Buildbox compiled exact clean pushed commit
  `9ed564adac77042d9d0dff9dabc98b6caa646aca` as release
  `7.1.3-gemini-i2c6-fwatt`. Package provenance and every packaged checksum
  passed; no native VM build ran.
- The independently reproduced Android-v0 candidate has raw SHA-256
  `7d8efed2f932e0a61e9417ae062fbb8b72b0baddc21c3857fb15093e0446c22b`
  and exact 16 MiB padded SHA-256
  `4bdaef917acd477839cdc3129b2fa4a63591e29c6fa912afd214bc9a1f5d0972`.
  All 32 LK gates, twelve inherited negative DT mutations, and two new
  attestation-window mutations passed.
- The runtime classifier accepts both structurally valid decision branches,
  rejects six unsafe mutations, exposes the immutable raw samples, and permits
  native return only after a complete capture.
- Guarded deployment resolved inactive live-GPT `boot2` as p30 while Gemian
  used p29. The exact write, sync, flush, full readback, and clean shutdown
  passed without a fresh backup or automatic reboot.
- The one permitted runtime attempt captured both samples. SCP reset control
  was `0x00000000` twice and debug PC was `0xfffffffe` twice. Every AP-visible
  Device-APC permission and master-domain word was zero, while control was
  `0x00000001`; all values were stable. The planned compound predicate failed,
  so the handoff faulted before creating an I2C6 client or transfer. CPUs 8--9
  stayed offline and no register write occurred.
- The collector sent its predeclared native reboot only after the complete
  capture, and a changed-identity Gemian boot returned. The quick reboot was
  therefore expected experiment behavior rather than unattributed failure.

## Analysis

The candidate correctly failed its frozen contract, but the observation also
exposed two defects in that contract. Pinned public Gemian source defines SCP
configuration offset `0x000` as reset control: zero asserts reset and one
releases/starts SCP. The stable zero observations are therefore positive
evidence that SCP remained reset. Offset `0x0b4` is the debug-PC register, but
the source does not justify requiring it to read zero while reset; its stable
`0xfffffffe` value remains diagnostic. Likewise, the stable all-zero AP view
of Device-APC AO cannot be treated as proof of the secure policy installed by
ATF.

This run did not execute the inherited stopped-DVFSP validation because the
compound gate faulted first. B1 therefore remains open. The corrected
successor must require reset control zero, record PC and Device-APC without
using them as pass predicates, run the stopped-DVFSP validation in the same
boot, and recheck reset control at both edges of every admitted read-only I2C6
transfer. See the
[`runtime result`](results/runtime-attempt-1-failed-closed-20260819.txt) and
[`contract correction`](results/runtime-attempt-1-contract-correction-20260819.txt).

## Conclusion

The exact candidate is complete and must not be repeated. It produced a valid,
failed-closed B1 observation with zero I2C6 transfers and zero writes. Gate-6
writing and CPU8/CPU9 admission remain closed.

## Follow-up

Implement one corrected read-only successor that combines live SCP reset hold,
same-boot stopped-DVFSP validation, and per-transfer reset checks around only
the already-proven provider reads. Advance to B2 only if that exact proof chain
passes. Do not enable a writable provider, DA921x write, or CPU request.
