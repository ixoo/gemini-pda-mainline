# Experiment: bind READY to one CPU8 admission candidate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-admission` |
| Status | `running` |
| Subsystem | arm64 late CPU profile and MT6797 CPU8 admission |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Can the exact serviceability-first CPU8 live-trigger profile reach the existing
one-shot admission controller only after the architecture-owned READY token is
published, while the generic configuration with the profile disabled still
compiles and passes through the late-target preflight?

The hardware-free hypothesis is that two independent defects currently prevent
that test: the profile-disabled header lacks its preflight stub and always-built
boot-capability prototype, and the production MT6797 profile still names the
older `699f1478...` configuration-input identity instead of the exact candidate
identity `5968c24f...`.

## Provenance and environment

- Parent kernel series: canonical Linux 7.1.3 series through patch `0434`.
- Parent prepared source state:
  `b347cf26c4201b6a37ad677f498a66a0097753b00c023d16a1d0bb0e96975de0`.
- Parent prepared source integrity:
  `1b5ba3d2f785fe4c4ed6cfb4b43452e99594575a31e05f487e14e7ce6883410f`.
- Candidate profile: `a72-admission-live-trigger-candidate`.
- Reconnaissance package:
  `linux-7.1.3-gemini-a72-admission-live-trigger-candidate-8b1ce2aa-5968c24f`.
- Candidate configuration-input SHA-256:
  `5968c24f1904c0559dea25480c41fbc7db49e822dc3600d1bdd7632330853f40`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

Patch generation, mutation testing, and compilation are hardware-free. The
repair adds no CPU request, CPU9 request, retry, CPU_OFF, partition write, or
device action. Its generated review is explicitly not a boot candidate.

Any later boot2 deployment remains subject to the repository's candidate,
partition-resolution, checksum, readback, and clean-shutdown gates. The first
runtime attempt may request CPU8 exactly once only after a root-only live token;
CPU9 remains vetoed.

## Associated code

- `scripts/generate-on-buildbox` pins and runs generation on the managed source.
- `scripts/generate_patches.py` emits and replays two logical format-patches.
- `scripts/source_edits.py` contains deterministic exact-anchor edits.
- `scripts/validate_source.py` validates the config-off and identity contracts.
- `scripts/test_mutations.py` proves representative unsafe changes are rejected.
- `scripts/build-candidate.sh` source-pins the proven ATAG/serviceability
  assembler and substitutes only the exact repaired Buildbox package.
- `scripts/validate-candidate.py` independently validates package provenance,
  linked symbols, Android-v0 layout, LK gates, padding, and negative mutations.
- `scripts/install-boot2.sh` source-pins the guarded live-GPT installer and
  retargets its exact predecessor, candidate, and experiment identities.
- `scripts/collect-pretrigger.sh` pre-arms the exact USB/netcat observation
  path, distinguishes an early return to changed-ID Gemian, and never triggers.
- `scripts/remote-pretrigger.sh` emits the bounded read-only live frame for the
  exact installed candidate.
- `scripts/validate-pretrigger.py` accepts only the exact serviceable,
  READY/controller-armed, zero-execution state while returning the new boot ID.
- `scripts/test-pretrigger.py` accepts the trace-aware READY schema and rejects
  nine unsafe state, trace, request, and schema mutations.

## Procedure

1. Generate two patches from the integrity-pinned post-`0434` source on
   Buildbox and fetch only the checksum-covered review.
2. Admit the patches in canonical order and audit every manifest profile.
3. Compile the default configuration-off control on Buildbox.
4. Compile the exact `a72-admission-live-trigger-candidate` profile on Buildbox.
5. Confirm the new package retains configuration-input identity `5968c24f...`,
   links the one-shot controller and READY consumer, and introduces no CPU9,
   CPU_OFF, or retry path.
6. Only then decide whether the package is the next boot2 candidate.

## Observations

- The exact pre-repair candidate profile compiled successfully at repository
  commit `6069088eb1e121934721aff1763dc3e6bc7a4687`.
- Its package records configuration-input identity `5968c24f...` and resolved
  configuration SHA-256 `9b9118fd...`.
- The linked production profile still expects `699f1478...`, so the package is
  reconnaissance-only: runtime binding would retain the blocker rather than
  publish READY.
- A separate default-profile control fails before link because
  `arm64_validate_late_cpu_preflight()` is undeclared when the profile is off,
  while always-built `arm64_late_cpu_validate_boot_caps()` lacks a visible
  prototype.
- Exact-source generation at repository commit `9b17b571` produced two logical
  patches with strict style, deterministic replay, positive source validation,
  and all nine rejecting mutations passing. The first generation attempt found
  and corrected a validator that counted only the production identity binding
  while the historical fixture intentionally owns a second comparison.
- Canonical patch `0435` is byte-identical to generated SHA-256 `f07cd67c...`;
  patch `0436` is byte-identical to generated SHA-256 `1a439a82...`.
- The admitted series passes all 158 manifest profiles and rejects all eight
  canonical-series invariant mutations.
- Buildbox compiled both exact commit `5abde763` controls. The default `full`
  profile now passes, closing the configuration-off defect. The enabled
  profile also passes as release `7.1.3-gemini-a72-admission-live`; its fetched
  package passes every checksum and retains configuration-input identity
  `5968c24f...`.
- The linked enabled image contains one READY accessor, preflight, live trigger,
  admission core, and `add_cpu()` wrapper. The controller object has exactly one
  external `add_cpu` dependency and the core materializes CPU `8`; it has no
  `remove_cpu`, `cpu_down`, CPU9 immediate, retry, or CPU_OFF path.
- Two independent Android-v0 constructions agree on raw candidate
  `4c8cf8e0...` and exact 16 MiB boot2 image `8acf9227...`. The independent
  validator passes all 32 LK gates, rejects six container corruptions, and
  confirms the serviceability DT and ramdisk are unchanged.
- The pre-trigger collector is source-pinned to the last proven USB/netcat
  observer and retargets only the exact full-partition candidate identity. Its
  materialized probe is deterministic at `68cbb6af...`; Bash, ShellCheck,
  positive-frame, and CPU-online mutation gates pass. It has no trigger path.
- A read-only deployment preflight could not begin because the device was
  powered off or otherwise unreachable. No device or partition action occurred.
- A later read-only preflight in known-good Gemian boot `0a0d0adb...` resolved
  inactive, unmounted live-GPT `boot2` as `/dev/mmcblk0p30`, with USB power
  online and the battery at 100%. The initial installer stopped before writing
  because its older lineage pin expected `fd611a4c...`; the independently read
  full-partition checksum was instead exact documented and readback-verified
  pmsg-witness candidate `0814c06b...`. The installer now admits only that
  exact current predecessor for this transition.
- Unsigned commit `3fce29f3` published that corrected guard before deployment.
  The retry matched exact predecessor `0814c06b...`, retained empty transition
  and admission records without writing retained RAM, wrote exact candidate
  `8acf9227...` only to inactive live-GPT boot2, synchronized and flushed it,
  matched the full-partition readback, removed its temporary readback, and made
  no fresh predecessor backup. Gemini then shut down cleanly without an
  automatic reboot; SSH failure plus three consecutive closed TCP/22 probes
  confirmed the power-off boundary.
- The first collector arm expired before physical selection and observed no
  device. After selection, exact Gemini USB appeared but macOS lacked its
  documented host address; restoring only `10.15.19.1/24` made the existing
  netcat service reachable. The immutable frame `c2ab936d...` then proved exact
  candidate `8acf9227...`, release `7.1.3-gemini-a72-admission-live`, boot ID
  `2ec43fd0...`, CPUs 0--7 online, CPUs 8--9 offline, and an armed controller
  with zero executions, requests, retries, or CPU_OFF operations.
- The initial validator rejected that safe frame only because it was pinned to
  the pre-`0421` controller schema and omitted the already-published
  `entry_trace_ret=0` and `terminal_trace_ret=0` fields. The corrected validator
  source-pins the later proven trace-aware schema, retargets the exact candidate
  and release, accepts the same immutable frame, and rejects nine unsafe
  mutations. No trigger was sent during either classification.
- Full generation and admission chronology is in
  [`results/generation-20260830.txt`](results/generation-20260830.txt).
- Exact compile, linked-audit, and candidate evidence is in
  [`results/build-and-candidate-20260830.txt`](results/build-and-candidate-20260830.txt).
- Exact pre-trigger tooling evidence is in
  [`results/pretrigger-tooling-20260830.txt`](results/pretrigger-tooling-20260830.txt).
- Exact live qualification and validator-correction evidence is in
  [`results/pretrigger-attempt-1-qualified-20260830.txt`](results/pretrigger-attempt-1-qualified-20260830.txt).
- The boot-bound follow-up consumed its exact token once and stopped with
  `operation_ret=-11`, `core_consumed=0`, advisory entry-trace `-EIO`, and
  zero CPU requests. Same-boot dmesg reports an unavailable static runtime
  identity and proof mask `0x75008`. The candidate retained serviceability DT
  `1478f2c8...` without the package-owned provenance leaf, so READY was never
  published. See the
  [sanitized one-shot result](../2026-08-30-mainline-a72-ready-admission-one-shot/results/runtime-attempt-1-ready-unpublished-20260830.txt).

## Analysis

The kernel-side deterministic blockers are closed: the feature-disabled
configuration compiles and the production profile identity matches the exact
candidate inputs. Candidate construction was incomplete, however. It replaced
the package DT containing the generated static identity record with the
serviceability DT and did not recompose the record. The pre-trigger check also
mistook an armed consumer for proof that the architecture READY producer had
succeeded.

## Conclusion

The repaired source and both Buildbox controls remain valid, but candidate
`8acf9227...` is retired after one decisive pre-core attempt. Its container
omitted the package-owned runtime provenance record, and no CPU request
occurred. This is not CPU8 hardware evidence.

## Follow-up

Reuse the exact Buildbox package but compose its generated provenance record
with the proven serviceability transform. Independently validate the DT delta,
container, and an explicit runtime-binding/READY precondition before one new
CPU8-only attempt. Keep CPU9 vetoed.
