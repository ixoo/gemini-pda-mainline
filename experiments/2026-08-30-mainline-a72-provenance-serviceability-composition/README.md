# Experiment: compose late-CPU provenance with the serviceability DT

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-provenance-serviceability-composition` |
| Status | `deployed to boot2 with full readback; device shut down awaiting selection` |
| Subsystem | arm64 late-CPU runtime identity and Gemini serviceability DT |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Does adding the exact package-owned provenance leaf to the already-proven
serviceability/admission DT preserve both contracts and allow the existing
architecture owner to publish READY before one CPU8-only attempt?

This changes only the DT supplied to the LK container. It reuses exact validated
Buildbox package commit `5abde763...`, Image, configuration, ramdisk, command
line, controller, and one-shot CPU8 request limits.

## Provenance and environment

- Exact Buildbox package commit:
  `5abde763316ab358d7f5cb1a3b6a461eb0a2ed99`.
- Package-owned DT SHA-256: `d3197c68...`; it contains exact generated A41
  record SHA-256 `05a3e54a...` and record identity `68b864d9...`.
- Retired candidate serviceability DT SHA-256: `1478f2c8...`; it lacks the
  package provenance leaf.
- Composed-DT builder: requires the exact package DT, package record JSON, and
  runtime-proven serviceability/admission DT before adding only the leaf.
- Build backend: no new kernel build; reuse of the exact validated Buildbox
  package only. No native VM build is used.

## Safety assessment

DT construction and validation are hardware-free. The controller remains
root-only and one-shot, with at most one CPU8 request and no CPU9, CPU_OFF,
retry, storage, firmware, or reboot path. CPU9 remains vetoed.

Any deployment remains subject to exact package, DT, container, live-GPT,
inactive boot2, power, padding, write, readback, and clean-shutdown gates.
Before any trigger, runtime qualification must directly observe verified
runtime identity and READY; an armed controller alone is insufficient.

## Associated code

- `scripts/build-composed-dtb.py`: cross-checks the package DT against its A41
  record JSON, then adds exactly that leaf to the serviceability/admission DT.
- `scripts/validate-composed-dtb.py`: independently parses all three DTBs and
  requires the exact logical-tree delta.
- `scripts/test-dtb-mutations.py`: rejects ten provenance, serviceability, and
  unexpected-node mutations.
- `scripts/build-candidate.sh`: source-pins the proven Android-v0/LK assembler
  and substitutes only the exact package and composed DT identities.
- `scripts/validate-candidate.py`: independently checks the exact package,
  layout, provenance, serviceability, controller, and six corrupt containers.
- `scripts/install-boot2.sh`: retargets the guarded live-GPT installer only to
  exact predecessor `8acf9227...` and candidate `f694ddb9...`.

Private DTBs and containers remain below ignored `artifacts/` paths.

## Procedure

1. Add the package DT's exact A41 leaf twice to serviceability/admission DT
   `1478f2c8...` and require byte-identical output.
2. Independently require the exact package-owned provenance property set,
   digests, record identity, and the already-proven serviceability delta.
3. Rebuild the LK container twice with the unchanged package Image, ramdisk,
   and command line; require byte-identical raw and padded artifacts.
4. Reject provenance, serviceability, container, CPU-path, and identity
   mutations before accepting a boot candidate.
5. Publish the exact definition and validation before any boot2 write.

## Observations

The prior runtime returned `-EAGAIN` before core consumption and reported the
static identity record unavailable or invalid. Source and artifact inspection
show that the Buildbox package DT contains the exact generated record, while
the separately selected serviceability DT used in candidate `8acf9227...`
does not. The kernel package does not need a speculative correction.

Two independent compositions produce byte-identical DT `8f87be2b...` from
exact serviceability/admission DT `1478f2c8...` and the package's exact A41
record. An independent binary FDT parser proves that the complete logical tree,
reservation map, boot CPU, serviceability nodes, controller, and binder are
unchanged except for one exact `/chosen/gemini-late-cpu-provenance` leaf. It
matches the package DT and record JSON byte for byte. Ten structural mutations
are rejected.

Two independent Android-v0 assemblies produce exact raw container
`1921c30e...`; two padding paths produce exact 16 MiB boot2 candidate
`f694ddb9...`. All 32 LK gates pass, the package and candidate manifests pass,
and six corrupt-container mutations are rejected. The Image, configuration,
ramdisk, command line, controller, one-CPU8 limit, CPU9 veto, zero CPU_OFF,
and zero retry paths are unchanged. Exact offline evidence is in
[`results/offline-candidate-validation-20260830.txt`](results/offline-candidate-validation-20260830.txt).

After the definition was published, the first installer invocation stopped
before device access because its outer artifact guard incorrectly pinned a
nested path rather than the required basename. The corrected guard was
published separately at commit `61b536c8`; its read-only preflight then passed
on exact Gemian boot `1df230e8...`, live-GPT inactive and unmounted
`/dev/mmcblk0p30`, exact predecessor `8acf9227...`, stable external power and
100% battery, and logically empty transition/admission retained records.

The guarded write targeted only logical `boot2`, synchronized and flushed it,
and required complete 16 MiB readback `f694ddb9...`. It made no fresh backup,
removed its temporary readback, wrote no other partition or retained RAM, and
then shut Gemini down without rebooting. SSH failure and three consecutive
closed TCP/22 probes confirm shutdown. Sanitized evidence is in
[`results/deployment-boot2-f694ddb9-20260830.txt`](results/deployment-boot2-f694ddb9-20260830.txt).

## Analysis

The smallest attributable change is to compose the two already-owned DT
inputs: retain the complete runtime-proven admission/serviceability tree and
add only the package-generated provenance leaf after cross-checking it against
the package record JSON. This closes the observed runtime-binding input without
changing CPU request code or treating an expected record as CPU-local runtime
evidence.

The prior pre-trigger validator's architectural blind spot must not recur.
Before consuming a new token, the live collector will require the positive
`verified the pre-finalization runtime identity binding` message, reject every
profile-blocked message, and retain the exact armed/zero-execution checks. An
armed controller alone is not sufficient.

## Conclusion

`deployed-exact-provenance-serviceability-candidate`: exact padded candidate
`f694ddb9...` is installed to boot2 with matching full readback and the device
is confirmed shut down. No CPU request occurred during deployment.

## Follow-up

On the next owner-selected boot2 start, require positive runtime identity, no
profile blocker, serviceability, and zero execution before defining a new
boot-bound one-shot. Do not trigger from an armed frame alone.
