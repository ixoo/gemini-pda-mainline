# Mainline MT6797 A72 BigiDVFS SRAM-LDO owner

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-27-mainline-a72-bigidvfs-sram-owner` |
| Status | canonical patches `0392`/`0393` validated; Buildbox compile pending |
| Subsystem | MT6797 CPU8 secure SRAM-LDO request and readback |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-27 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, CPU8 physical binding |

## Question or hypothesis

Can the existing read-only BigiDVFS backend safely grow one serialized,
attempt-bound, one-shot request for the exact CPU8 SRAM-LDO state, prove that
request with independent stable selector/calibration reads, and remain
unreachable from production until the complete CPU8 binder exists?

## Provenance and environment

- Parent repository commit:
  `06debdf2c933b40bce5bf4af2fce579f49d5aa43`.
- Canonical parent series: 380 entries through `0391`.
- Managed prepared-source state:
  `f3f425c07115cc7381b75c7f751b1651a2e5d90f710c6302468ae775d1043ea5`.
- Current BigiDVFS implementation SHA-256:
  `454c4bf3d3d049d0586a86784d0a101067005863b1e18190f9d0ddaf5be8932d`.
- Build backend: Buildbox only.
- Boot path and target partition: none in this phase.
- Protocol evidence: the retained secure-firmware audit identifies implemented
  AArch64 SRAM-LDO set FID `0xc20003bf`, exact argument units, selector and
  calibration registers, and the independent `REG_READ` FID `0xc200035f`.

## Safety assessment

Generation, compilation, and QEMU use no device. The production owner is behind
a new default-off option and has no caller. The focused KUnit suite invokes an
in-memory transport and records the secure request, delay, and reads without
calling SMCCC or touching physical hardware. No boot image or candidate is
selected.

The owner exposes no inverse, disable, retry, generic voltage, raw-register, or
userspace interface. It accepts only the fixed 1.1 V CPU8 transaction after
caller-attested provider and isolation completion. Once the secure service is
attempted, every outcome seals the owner and later recovery remains reset-only.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the resource owner, exact sequence, result
  vocabulary, one-shot boundary, and proof requirements.
- `templates/` contains independently written production and injected-test
  snippets for deterministic patch generation.
- `scripts/source_edits.py` applies the two logical source changes.
- `scripts/validate_source.py` rejects protocol, ownership, order, caller, and
  hardware-free-test drift.
- `scripts/generate-patches.py` creates, checks, and replays two normal format
  patches from the exact prepared source.
- `scripts/generate-on-buildbox` pins the managed source state and bounded
  output package.
- `scripts/run-kunit-qemu` and `scripts/classify-kunit.py` accept only the exact
  pushed Buildbox package and focused no-network suite.
- Canonical patches `0392` and `0393` contain the byte-exact validated
  production owner and injected KUnit suite.
- [`results/generation-8b93e3cf.txt`](results/generation-8b93e3cf.txt) records
  the exact generator, source-state, patch, and safety identities.

## Procedure

1. Generate one production-owner patch and one injected-test patch from the
   exact through-`0391` prepared source.
2. Require strict Checkpatch, production/test validation, exact replay, and
   package checksum validation before admission.
3. Admit the two exact patches and one focused configuration profile.
4. Build the exact clean pushed commit on Buildbox.
5. Run the sole focused suite in bounded no-network arm64 QEMU.
6. Publish sanitized evidence before beginning the PSCI/generic-hotplug
   lifecycle bridge.

## Observations

The current backend serializes its four-word stable readback with one mutex and
has no writable API. Firmware evidence establishes the set FID but also proves
that it always returns zero and that the header-declared getter is absent from
the retained payload. The historical successful CPU8 path therefore used one
set request followed by two independent selector/calibration samples through
`REG_READ`.

The first Buildbox generation attempt from repository commit
`bd0da7fbbc81c38a38ba664df547ee2be1722447` reached the exact prepared source
but stopped before patch emission with `shared backend serialization: order
changed`. The validator had searched the whole backend and selected the
pre-existing read-path mutex rather than the new public adapter. The corrected
validator bounds the internal execution and public adapter functions
independently; no production or test template changed as a result.

The second Buildbox generation attempt from repository commit
`1cd1cf8aa99107d859bba625bd24375ff40fc5e0` passed the source validators and
then stopped before patch emission because strict Checkpatch reported 17
function-signature and continuation-alignment checks, with zero errors and
zero warnings. The templates were normalized to the canonical kernel style;
the API, transaction order, state machine, and test behavior did not change.

The third Buildbox generation attempt from repository commit
`8b93e3cf6e8437a4cd5c2802525fbdb5949212cb` passed production, test, and exact
replay source validation plus strict Checkpatch for both patches. The bounded
package contained exactly `0392` and `0393`; its checksums verified after the
only permitted package fetch. The canonical copies are byte-identical to that
package.

## Analysis

Reusing the backend mutex preserves a single resource owner. Treating the set
return or the unavailable getter as verification would weaken the established
boundary. A dedicated exact request plus stable raw readback preserves the
successful ordering while keeping general DVFS, voltage selection, CPU_ON,
and recovery policy outside this owner.

## Conclusion

Source implementation, style, and replay proof pass. Buildbox compilation and
focused QEMU runtime proof remain pending. No hardware support claim follows
from the source audit or contract.

## Follow-up

After exact patch generation, Buildbox compilation, and focused QEMU pass,
advance the roadmap to the PSCI/generic-hotplug lifecycle bridge. Do not build
or write a device candidate before the complete binder passes its own
hardware-free gates.
