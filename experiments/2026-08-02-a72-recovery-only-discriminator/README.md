# Experiment: A72 recovery-only watchdog/pstore discriminator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-recovery-only-discriminator` |
| Status | `deployment-ready` |
| Subsystem | Gemian watchdog kicker, MT6797 TOPRGU, console-ramoops |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-02 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 4 recovery prerequisite |

## Question or hypothesis

Can an experiment-only Gemian kernel transfer exclusive ownership of the
application watchdog from the normal per-CPU kicker, arm a bounded reset-only
deadline, persist an exact console-ramoops marker, and return to known-good
Gemian without performing any Cortex-A72 action?

## Safety boundary

The discriminator rejects every CPU8 and CPU9 boot callback before the vendor
external-buck preparation or PSCI call. It contains no DA921x, A72 SPM,
external-isolation, SRAM-LDO, PSCI CPU-on, MP2 DCM, CPU-online, or CPU-off
operation. It has no userspace control.

The watchdog handoff runs once from delayed work after the ordinary kicker has
initialized. Under the kicker's own lock it stops future kicks and invokes one
TOPRGU-owner operation while CPU-hotplug exclusion closes the only no-lock
reload caller. That operation takes the TOPRGU register lock, blocks later
ordinary restart calls, programs a fixed 12-second reset-only deadline,
reloads it once, and returns exact readback. A pre-ownership failure restores
normal kicker and hotplug service. Any result after ownership is terminal and
must reset.

## Evidence contract

The exact terminal marker is:

```text
gemini-a72-recovery-v1 stage=armed timeout=12s a72=forbidden
```

The known-good Gemian boot after expiry must establish a changed boot ID, a
watchdog-class reset reason, the exact recovered console-ramoops marker, CPU8
and CPU9 offline, and unchanged `boot2`. A visual reboot alone is inconclusive.

## Associated code

- `scripts/source_edits.py` performs three deterministic, source-drift-checked
  edits against the pinned public Gemian source.
- `scripts/generate-on-buildbox` generates reviewable `git format-patch`
  output with a synthetic, non-certifying experiment identity.
- `scripts/validate_patches.py` enforces the ownership, ordering, fixed-timeout,
  no-A72, no-userspace, and terminal-marker contract.
- `scripts/test_static.py` proves unsafe mutations are rejected.
- `patches/series` is the exact accepted three-patch Buildbox-generated review
  series.
- `results/patch-generation-review-20260802.txt` records the rejected first
  ownership design and accepted race-closed generation.
- `scripts/build-on-buildbox` performs the separate changed-versus-unpatched
  full compile, configuration, diagnostics, symbols, and stack review.
- `scripts/assemble.py` and `scripts/build-candidate.sh` construct the exact
  kernel-only Android-v0 payload replacement twice and independently pad it to
  the 16 MiB `boot2` size.
- `scripts/install-boot2.sh` source-pins the established live-GPT-resolving,
  predecessor-checking, full-readback, cleanup, and shutdown workflow.
- `results/compiler-and-container-review-20260802.txt` records the accepted
  compile, disassembly, stack, and offline container identities.
- `results/deployment-readiness-20260802.txt` pins the candidate, predecessor,
  guarded installer, cycle collector, timing expectations, and result map.

## Current decision

`offline-gates-passed-deployment-ready`: patch generation, ten mutation
tripwires, changed-versus-unpatched full compilation, binary ordering review,
two container assemblies, two padding methods, and the source-pinned guarded
installer pass. One exact deployment to live-GPT-resolved inactive `boot2` is
now authorized under the standing project policy. The installer must shut the
device down; the owner then manually selects `boot2`. Expect roughly 15 seconds
before watchdog takeover and a reset about 12 seconds later. The expected
screen and console state are deliberately unspecified; only changed-boot-ID
Gemian recovery plus the exact pstore marker can pass the gate.
