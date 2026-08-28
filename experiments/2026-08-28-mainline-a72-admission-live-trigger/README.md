# Experiment: serviceability-first CPU8 admission trigger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-live-trigger` |
| Status | `definition ready; hardware-free proof pending` |
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

Runtime collector, candidate construction, guarded boot2 installation, and
classification scripts are intentionally deferred until hardware-free source
proof passes. Private captures and candidates remain below ignored
`artifacts/` paths.

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

## Analysis

The new experiment separates two questions in one physical selection. If the
armed frame never appears, the current DT/supplier population is nonserviceable
even without controller activation. If it appears, the kernel and observation
channel are proven before the action. A subsequent disconnect or reset is then
localized to supplier resolution or the admission transaction, while a
returning status identifies a precise terminal error or CPU8 outcome.

## Conclusion

The retained-earlier-anchor direction is rejected. The serviceability-first
one-shot trigger is selected for hardware-free implementation and proof; no
kernel build, candidate, boot2 write, or physical CPU request has occurred in
this definition phase.

## Follow-up

Generate and prove the two canonical patches on Buildbox. The ordered next
step remains owned by `docs/ROADMAP.md`.
