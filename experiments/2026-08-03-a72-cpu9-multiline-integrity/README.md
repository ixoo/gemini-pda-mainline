# Experiment: CPU8/CPU9 multi-cacheline integrity

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-multiline-integrity` |
| Status | `offline-container-validated` |
| Subsystem | MT6797 retained Cortex-A72 pair and cache coherency |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 CPU9 coherency/load |

## Question or hypothesis

After reproducing the exact 1,024-round scalar pair-v4 oracle, can retained
CPUs 8 and 9 alternately publish and verify deterministic payloads across a
16 KiB, 256-cacheline shared working set for 64 bounded rounds without a data
mismatch, callback error, lost watchdog recovery, or changed power boundary?

## Provenance and environment

- Exact parent experiment:
  `2026-08-03-a72-cpu9-bounded-coherency`.
- Exact parent repository compile commit:
  `938cdefde98522a2cd3504605aee04e4c83d5671`.
- Exact parent coherence patchset SHA-256:
  `d4c40577b9e91fedfde048b29cb203311de264c526c71e3abd907fc6fafcf67f`.
- Exact parent full boot2 SHA-256:
  `eda1d5bb312aa937e41499ea8fd13a5f8ae95865399605fe7cf93ee61daaa23d`.
- Parent runtime: two exact pair-v4 passes with 1,024/1,024 final sequences,
  zero coherence errors, complete HPS CPU9 `-EPERM` attribution, watchdog-class
  recovery, offline recovery CPUs 8/9, and unchanged boot2.
- Build backend: Buildbox only; no native VM kernel build.
- Buildbox generated and validated the exact one-file source patch from clean
  repository commit `c9344a8a452077829ba2ac3142eeddc5e7215646`.
- Generated kernel commit:
  `f465d671ed82fd2a461c7a6b0f567452e70400d8`.
- Accepted patch SHA-256:
  `7dbbf400f2402c7763ae9fee73438b056086f459060749de8f4506e9638f83c0`.
- No deployment or runtime claim exists yet.
- Buildbox compile commit:
  `fb647817cd573e3dd8719821da8742bc5433979b`.
- Child `Image.gz-dtb` SHA-256:
  `81f076198ae314d187790beecee8d9b5edda3c4432e51a0f36a22dbe326fc468`.
- Exact pair-v4 parent `Image.gz-dtb` SHA-256:
  `ef0c1486f9f74a69e064a589a5229df30420f0235ec6fc5df03f489880d7235a`.
- Raw Android-v0 SHA-256:
  `4e3c1b1095ee87e0af3c45595ea83d859d53188a53aba10672202bf45938986a`.
- Full boot2-sized SHA-256:
  `5227729e34ca42cf606f43008ec753fce15147693ce7a670818db58c5903fa48`.

## Safety assessment

The child may add only a second, finite CPU0-owned observation phase after the
unchanged scalar phase passes. It must not alter CPU startup, the scalar
callback, HPS veto or timing, CPU_OFF prohibition, regulator/clock/reset/MMIO
state, watchdog timing, pair sampling, userspace control, or recovery. Every
wait and data loop has a compile-time bound; the worker publishes a complete
terminal snapshot before the inherited watchdog restart.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact working set, data oracle, synchronization,
  bounds, terminal, result classes, source invariants, and safety boundary.
- [`patches/`](patches/): the accepted experiment-only source patch.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): exact pair-v4 versus
  pair-v5 compile, binary, configuration, diagnostics, and stack comparison.
- [`results/patch-generation-review-20260803.txt`](results/patch-generation-review-20260803.txt):
  exact Buildbox generation identities and acceptance boundary.
- [`results/compile-review-20260803.txt`](results/compile-review-20260803.txt):
  exact comparative compile, binary, diagnostics, and stack evidence.
- [`results/offline-container-review-20260803.txt`](results/offline-container-review-20260803.txt):
  two-root Android-v0 reproduction and embedded-image validation.

## Conclusion

`offline-container-validated`: Buildbox reproduced the exact
pair-v4 parent, passed its static validator, applied the deterministic child
transformer, rejected all 16 multiline mutations, and generated a patch that
changes only `arch/arm64/kernel/psci.c`. The pinned comparative build passed its
source, configuration, diagnostics, linked-code, terminal, and stack gates. The
exact image was assembled twice into byte-identical Android-v0 and padded
containers with the expected embedded kernel and unchanged known-good ramdisk.
It must still pass guarded deployment/runtime-map gates before device access.

## Follow-up

Prepare and test the guarded boot2 installer, runtime evidence collector, and
pair-v5 recovery decision map before any device write.
