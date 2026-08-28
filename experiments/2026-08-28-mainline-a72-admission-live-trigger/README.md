# Experiment: serviceability-first CPU8 admission trigger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-live-trigger` |
| Status | `complete; attempt 1 failed before live frame, zero-trigger, retired` |
| Subsystem | MT6797 A72 admission controller, sysfs, CPU hotplug |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 7, attributable CPU8 admission |

## Question or hypothesis

Can the exact current CPU8 admission transaction be held dormant until the
known USB/netcat service is live, then invoked once from an exact root-only
token so that every physical attempt has an attributable pre-trigger frame?

The hypothesis is about observation timing, not a new CPU transaction. The
controller still derives CPU8 from the same physical source, publishes P17/P18,
and calls `add_cpu(8)` at most once. CPU9, CPU_OFF, retry, and automatic probe
activation remain absent.

## Provenance and environment

- Exact parent: canonical Linux source through patch `0418`.
- Prepared Buildbox source state and integrity: pinned in `contract.json`.
- Build backend: Buildbox only; no native VM build is authorized or used.
- Physical parent result: exact durable candidate `60902c7b...` produced no
  console or mainline USB before automatic Gemian return. Recovery found all
  three retained records logical-empty, so the candidate was retired.
- Positive control: the Stage-27 DT control reached `/init`, USB/netcat, and an
  eight-A53 baseline while the same retained early records remained empty.
  Therefore missing retained records are not a valid negative execution oracle.
- Patch `From:` metadata uses the clearly synthetic, non-certifying experiment
  identity and has no `Signed-off-by`. It is not submission-ready.

## Safety assessment

The default action is inert. With the new default-off mode selected, controller
probe only allocates boot-local state and exposes a root-only one-shot sysfs
endpoint plus read-only status. It does not resolve suppliers, register a
physical source, publish an owner state, write retained RAM, or request a CPU.

The exact token is consumed atomically before any supplier resolution. Invalid
or repeated writes cannot execute the action. The first valid write remains
consumed even if supplier resolution or admission fails. The existing core
then retains its independent one-shot gate and maximum of one `add_cpu(8)`
call. CPU9, CPU_OFF, retry, watchdog reset, reboot, firmware, storage, and
partition operations are absent.

The runtime collector must durably retain an exact pre-trigger frame before it
temporarily remounts the virtual sysfs writable. That frame proves the kernel,
boot ID, USB interface, CPU0-7 online/CPU8-9 offline, the unique armed endpoint,
and zero trigger executions. It restores sysfs read-only on every returning
path. A transport loss or reset after the single token is a terminal result;
the trigger is never retried. Retained records are corroborating evidence only.

Any eventual boot2 installation uses the standing-authorized live-GPT gates,
full-partition readback, and clean shutdown. It does not create a fresh device
backup and never reboots Gemian automatically after the write.

## Associated code

- `DESIGN.md`: exact endpoint, token, ordering, and decision contract.
- `contract.json`: prepared-source, parent-file, and bounded-effect identities.
- `scripts/source_edits.py`: deterministic two-stage source edits.
- `scripts/validate_source.py`: source ordering and effect validator.
- `scripts/generate-patches.py`: two logical format-patches plus replay.
- `scripts/generate-on-buildbox`: exact clean-commit Buildbox entry point.
- `scripts/validate.py`: local definition and mutation validator.
- `scripts/run-kunit-qemu`: clean, published, exact-package QEMU gate.
- `scripts/classify-kunit.py`: exact two-suite/15-case KTAP classifier.
- `scripts/build-candidate.sh` and `scripts/validate-candidate.py`: independent,
  source-pinned LK construction and validation.
- `scripts/install-boot2.sh`: live-GPT, predecessor-gated, full-readback boot2
  installer with mandatory clean shutdown and no fresh partition backup.
- `scripts/collect-live-trigger.sh`: exact-MAC USB watcher, durable pre-trigger
  commit, one trigger session, and no-retry recovery monitor.
- `scripts/remote-pretrigger.sh`, `scripts/validate-pretrigger.py`,
  `scripts/remote-trigger.sh`, and `scripts/classify-attempt.py`: exact live
  identity, armed-state, token, terminal-state, and transport-loss contract.
- `scripts/collect-pretrigger-recovery.sh`: source-pinned, read-only changed-ID
  Gemian, boot2, pstore, and retained-record recovery.

Private captures and candidates remain below ignored `artifacts/` paths.

## Procedure

1. Validate the dormant-trigger definition and unsafe mutations locally.
2. Commit, sign, push, and generate the two exact patches on Buildbox.
3. Review, replay, integrate, and compile an isolated KUnit profile on Buildbox.
4. Run the focused no-network KUnit suite and prove the one-shot trigger gate.
5. Define the production profile and a pre-armed USB/netcat collector.
6. Build and validate one exact production candidate on Buildbox.
7. Install only the live-GPT-resolved inactive boot2, verify full readback, and
   shut Gemian down.
8. Select boot2 once. Trigger only after the pre-trigger frame is durable.
9. Classify the returning result without retry and publish sanitized evidence.

## Observations

The audit found three earlier retained anchors at pure/core initcall,
subsys/fs initcall, and driver-init/probe boundaries. All returned exact-empty
after automatic Gemian recovery. More importantly, a kernel independently
proven live through `/init` and USB/netcat returned the same empty record state.
Moving the marker earlier within that ramoops region would therefore repeat a
disproven evidence channel.

The existing controller currently resolves all four suppliers and immediately
runs the admission core from `late_initcall` probe. That places the risky action
before the established userspace network observer. The proposed mode moves
supplier resolution and the unchanged core behind the one-shot endpoint.

The first exact-source Buildbox generation at `a6353c01` passed both semantic
source stages and stopped during strict review of production patch `0419`.
Function continuation layout, one alignment, an overlong commit description,
and comments for acquire/release ordering were corrected. The rejected attempt
admitted no patch package and performed no build or device action.

The second generation at `bc63b46d` made production patch `0419` strict-clean
and reached test patch `0420`. Its only finding was an overlong test-patch
commit description; the generated code had zero warnings and zero checks. The
description is now wrapped. Again, no patch package, build, or device action
was admitted.

The third exact-source generation at `48c367ff` passes both semantic stages,
strict review, package checksums, and full replay. Canonical patches `0419` and
`0420` are byte-identical to the validated package. The isolated
`a72-admission-live-trigger-kunit` profile is selected, and all 155 manifest
profiles remain canonical-order subsequences of the 412-entry series. No kernel
or device action had occurred at that generation boundary.

Exact clean commit `cc6e7f20` then compiled on Buildbox as
`7.1.3-gemini-a72-admission-live-kunit`. The fetched package has a complete
passing checksum manifest, exact profile and commit provenance, both focused
KUnit configurations, the live-trigger configuration, and the required trace,
trigger, and controller symbols. No native VM build or device action occurred;
the package remains hardware-free and is not a boot candidate.

The exact published harness at `03ce2d1a` ran that unchanged package on QEMU
`virt` with one single-threaded four-vCPU Cortex-A53 TCG instance and no
network. Both focused suites passed: six immutable-trace cases and nine
controller cases, including the three live-trigger cases, for 15 of 15 with
zero failures or skips. The bounded run ended only at the expected post-test
rootfs panic and timeout. There was no physical DT match, CPU request, CPU_OFF,
retry, device action, or boot candidate.

The separate production profile is now named
`a72-admission-live-trigger-candidate`. It keeps the complete physical source
and owner chain plus modules needed by the established serviceability ramdisk,
enables the default-off live trigger, excludes KUnit and split startup, and
uses release `7.1.3-gemini-a72-admission-live`. The controller remains inert at
probe because the live-trigger mode is compiled in. All 156 manifest profiles
remain canonical-order subsequences of the 412-entry series.

Exact clean commit `c147e2dd` compiled that production profile on Buildbox as
`7.1.3-gemini-a72-admission-live`. All 565 entries in the fetched package
manifest pass. The build is pinned to patchset `40a78b77...`, resolved config
`265f610b...`, `Image` `96c86abe...`, `Image.gz` `4b884c01...`, and unchanged
production DTB `1bd6ce2d...`. No native VM build or device action occurred.

Two independent LK constructions agree on raw container `633f897a...` and the
exact 16 MiB boot2 image `4e0f8688...`. The established serviceability ramdisk
is unchanged at `e0dffa04...`; the name is `gemini-a72live`, the command line is
`bootopt=64S3,32N2,64N2`, and all 32 LK gates pass. Independent validation finds
one controller, one binder, no standalone observer, one CPU8 request maximum,
and zero CPU9, CPU_OFF, or retry paths.

The runtime tooling now matches the kernel's exact full sysfs wire, including
`operation_ret`, `cpu_requests`, and every zero-bounded counter. One accepted
armed branch and three terminal branches pass; thirteen unsafe mutations fail
closed. The host must fsync the accepted pre-trigger frame and trigger intent
before opening the sole trigger connection. A commit-bearing transport loss is
terminal and cannot be retried. No runtime tool requests a reboot.

The guarded deployment then ran from known-good Gemian boot ID
`e3731f9a-...`. Live GPT resolved root as `/dev/mmcblk0p29` and inactive
logical boot2 as `/dev/mmcblk0p30`. Exact predecessor `60902c7b...`, stable
external power, 100 percent battery, unchanged TEE identities, and empty
transition/admission retained records passed. The write was synced and flushed;
the full-partition readback matched `4e0f8688...`. No fresh backup or retained
RAM write occurred. Gemian was cleanly shut down, then three consecutive TCP/22
closures confirmed it unreachable.

The host collector was armed before the owner selected boot2. The owner saw no
console, but screen state remains contextual. Across the selected boot, the
host observed neither accepted Gemini USB MAC, opened no pre-trigger session,
and had no mainline identity. It therefore wrote no trigger token and executed
no CPU8 admission action. Gemian returned with changed boot ID
`7be70bda-...`; that authoritative observation ended the wait without a retry.

Read-only post-return recovery confirmed the 16 MiB boot2 partition still
matched `4e0f8688...`, with zero pstore files, a logical-empty transition
ledger, and empty admission entry/terminal records. Those retained results are
corroborating only. The primary classification is
`pretrigger-nonserviceable-zero-trigger`: this physical selection did not test
the CPU8 trigger hypothesis. The artifact is retired and cannot be repeated.

## Analysis

The experiment separated the questions as intended. The armed frame never
appeared, so the current production kernel/DT/configuration population did not
establish the required serviceability baseline even with supplier resolution
and admission disabled at controller probe. Since the token was never written,
this result says nothing about whether the unchanged admission transaction can
bring CPU8 online. It does show that deferring that transaction alone is not
sufficient to recover the observation channel.

## Conclusion

The retained-earlier-anchor direction remains rejected, and the live trigger
remains hardware-free proven. Physical attempt 1 is conclusively a
zero-trigger pre-serviceability result: no CPU8 request occurred and CPU8
support is not advanced. Candidate `4e0f8688...` is retired.

## Follow-up

The exact attempt and recovery receipt are complete. The ordered next step
remains owned by `docs/ROADMAP.md`.
