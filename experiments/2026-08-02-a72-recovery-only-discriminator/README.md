# Experiment: A72 recovery-only watchdog/pstore discriminator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-recovery-only-discriminator` |
| Status | `patch-review-passed` |
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

## Current decision

`patch-generation-accepted-compile-pending`: the exact generated patches and
ten mutation tripwires pass. Full changed-versus-unpatched compilation is now
authorized on Buildbox. This record still does not authorize candidate
construction or device action.
