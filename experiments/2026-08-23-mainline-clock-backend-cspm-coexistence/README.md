# Experiment: clock-backend CSPM coexistence

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-clock-backend-cspm-coexistence` |
| Status | exact candidate admitted; named-device evidence pending |
| Subsystem | DVFSP handoff, CSPM ownership, I2C6, DA921x |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-23 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, protected clock-read qualification |

## Question or hypothesis

Can the handoff remain the sole owner of the CSPM resource while the read-free
clock backend binds through an explicit access-controller relationship and the
complete I2C6/DA921x serviceability baseline remains available?

The predecessor proved clock driver init, platform population, probe entry,
and read-free probe completion, but its independent CSPM resource request made
the handoff fail with `-EBUSY`. This successor changes that ownership model; it
does not attempt a protected read.

## Provenance and environment

- Foundation evidence: signed commit `d61b89c6` and the predecessor's
  [split runtime result](../2026-08-23-mainline-clock-backend-first-dmesg-entry/results/runtime-attempt-1-read-free-pass-resource-conflict-20260823.txt).
- Canonical patch:
  `0335-soc-mediatek-share-CSPM-through-MT6797-handoff.patch`.
- Parent profile: `da921x-clock-entry-first-dmesg`.
- New profile: `da921x-clock-cspm-coexistence`.
- Expected release: `7.1.3-gemini-clock-cspm-coexist`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The clock backend remains default off. The new base-DT contract removes CSPM
from its `reg` list, retains only the disjoint MCUMIXED aperture, and names the
already-enabled handoff as its access controller. The handoff's callback is
serialized by the same lock order as I2C6 admission and holds the full transfer
lease until the callback returns.

The first runtime enables only the read-free clock node. It retains the two
already-qualified driver-init/probe-entry records, but instantiates no
protected-read observer or BigiDVFS backend. The clock callback therefore stays
dormant: no CSPM semaphore, MCUMIXED, protected-clock, secure, regulator, CPU,
storage, reset, or power transaction is requested by this experiment.

## Associated code

- `patches/v7.1.3/0335-soc-mediatek-share-CSPM-through-MT6797-handoff.patch`
- `configs/gemini-clock-backend-cspm-coexistence.fragment`
- `contract.json`
- `scripts/validate.py`
- `scripts/test-validate.py`
- `scripts/build-serviceability-clock-dtb.sh`
- `scripts/build-candidate.sh`
- `scripts/test-candidate.py`
- `scripts/install-boot2.sh`
- `scripts/remote-runtime-probe.sh`
- `scripts/validate-runtime.py`
- `scripts/validate-retained.py`
- `scripts/collect-runtime.sh`
- `scripts/test-runtime-tools.py`

The exact pushed revision passed Buildbox. Candidate construction,
installation, and runtime tooling pin its package identities and fail closed on
any changed source, artifact, DT contract, partition identity, or runtime
oracle.

## Procedure

1. Validate the single-resource DT, access-controller edge, handoff-owned
   callback, I2C6 lock ordering, exact profile derivation, canonical-series
   invariant, default-off closure, and zero-caller runtime scope.
2. Commit and push the definition, then build the exact revision with
   `KERNEL_PROFILE=da921x-clock-cspm-coexistence ./scripts/build-kernel --backend buildbox`.
3. Fetch only the validated package and independently construct the exact
   serviceability-plus-clock candidate.
4. Install to live-GPT `boot2` under the standing checksum/power gates and
   shut down after full-partition readback.
5. Capture one physical boot selection. Require the handoff bound and ready,
   one clock backend, a single CSPM owner in `/proc/iomem`, I2C6 plus DA921x,
   CPUs 0--7, USB/netcat, keyboard, and unchanged zero-action counters.
6. Return to changed-ID Gemian only after classification and recover the two
   retained entry records if needed.

## Decision map

- Full serviceability plus the exact coexistence marker qualifies the shared
  ownership model for a separate one-protected-read experiment.
- A remaining `-EBUSY`, missing handoff/I2C6/DA921x, or more than one CSPM
  owner rejects the candidate and localizes the next action to resource or
  supplier ordering without a protected call.
- A bound but non-ready handoff localizes the failure to the inherited handoff
  oracle; do not weaken it to make the clock backend bind.
- Any protected-read, BigiDVFS, clock-enable, DA921x data-write, or CPU action
  rejects attribution.

## Observations

The definition validator and all 10 unsafe mutation cases pass. The all-profile
series audit covers 116 profiles and 327 canonical patches. The patch applies
cleanly to the exact prepared Buildbox source and strict checkpatch reports
zero errors, warnings, or checks after excluding only the required missing-DCO
message for its clearly synthetic non-certifying author. See the
[prebuild definition result](results/prebuild-definition-20260823.txt).

Exact commit `67e40d761f9e83063742a8e36ffb001c6fa3d38e` passed Buildbox as
`7.1.3-gemini-clock-cspm-coexist`; the fetched package revalidated locally.
Two independent serviceability/clock DT derivations are byte-identical, as are
two raw LK assemblies and two full-partition padding constructions. The
candidate passes all 32 LK gates and an independent validator that rejects all
19 unsafe DT mutations. Its raw SHA-256 is `dc093771...e6f2`; the exact
16-MiB boot2 image SHA-256 is `ae401044...24e7`. The live/recovery tools reject
35 and 12 unsafe mutations respectively. No device access or hardware write
occurred during admission. See the [Buildbox result](results/build-67e40d76-success.txt)
and [candidate admission](results/candidate-admission-dc093771.txt).

## Analysis

Build and offline admission pass. Named-device coexistence evidence remains
pending and is the only basis for qualifying this ownership model.

## Conclusion

The exact candidate is admitted for one named-device boot. A compile and
offline admission establish only source/configuration/container coherence;
only that runtime can qualify resource coexistence.

## Follow-up

Only a coexistence pass may advance the roadmap to exactly one protected clock
read with before-call and after-return attribution.
