# Mainline CPU8 PSCI/generic-hotplug lifecycle bridge

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-27-mainline-a72-hotplug-lifecycle-bridge` |
| Status | contract frozen; implementation pending |
| Subsystem | arm64 PSCI acceptance, secondary completion, and generic CPUHP continuation |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-27 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, CPU8 physical binding |

## Question or hypothesis

Can the proven synchronous transition executor be split at Linux's real CPU
lifecycle ownership points, preserving one CPU_ON and reset-only failure, while
leaving generic arm64 completion, timeout, and CPUHP ordering authoritative and
keeping all production CPU8 admission closed?

## Provenance and environment

- Parent repository commit:
  `d3381e1a9827a02907e6e4a615b2aa27eb81518b`.
- Canonical parent series: 382 entries through `0393`.
- Canonical series SHA-256:
  `2304d0c5d22ad84afd6e6ad60d60a390079c09f7c91c47efd0e9f5defeaf63ec`.
- Manifest SHA-256:
  `46cc91d8b61eb575c34198025b3cf0341a458137cc5af5a45ad1c25c507790a5`.
- Managed prepared-source state:
  `fbd9f19e0eeb36540d922bb65965afbf1a329d15c3f113f82b8a4443367f5246`.
- Build backend: Buildbox only.
- Boot path and target partition: none in this phase.

Exact source identities and lifecycle locations are recorded in
[`results/source-lifecycle-map-20260827.txt`](results/source-lifecycle-map-20260827.txt).

## Safety assessment

This milestone is hardware-free. The existing MT6797 `.cpu_boot` callback
continues to return `-EAGAIN`, the new optional lifecycle callbacks remain
unset in its operation table, and no late caller is added. KUnit uses only
injected functions and QEMU has no MT6797 hardware. No physical PSCI, CPU,
IPI, DCM, MMIO, retained-RAM, watchdog, regulator, partition, reboot, or device
operation is selected.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes lifecycle ownership, hook placement, pause
  and resume semantics, failures, and test boundaries.
- [`contract.json`](contract.json) records the exact machine-readable source
  and ownership map.
- `templates/` will contain independently written source and test snippets.
- `scripts/` will deterministically generate, validate, replay, build, and run
  the exact focused result through Buildbox.

## Procedure

1. Add no-op-by-default arm64 operation callbacks immediately after successful
   secondary completion and full generic CPUHP completion.
2. Refactor the executor into begin, secondary-complete, full-complete, and
   generic-failure transitions while preserving its synchronous injected test
   composition.
3. Exhaustively test phase order, failures, one-shot behavior, and unchanged
   rollback/retention rules using only injected callbacks.
4. Generate two normal format patches from exact prepared source, require
   strict Checkpatch and exact replay, and audit all manifest profiles.
5. Build the admitted clean commit on Buildbox and run the sole focused suite
   in bounded no-network arm64 QEMU.
6. Publish evidence before the complete physical binder is assembled.

## Audit observations

`cpu_psci_cpu_boot()` calls `psci_ops.cpu_on()` and returns firmware acceptance.
Arm64 `__cpu_up()` then waits five seconds on its private `cpu_running`
completion and returns success only after `secondary_start_kernel()` has set
the online bit. Generic `bringup_cpu()` subsequently synchronizes the AP,
waits for `CPUHP_AP_ONLINE_IDLE`, and drives the AP to the requested target.
The current executor instead calls CPU_ON, a private ten-second online-wait
callback, IPI, and DCM synchronously; using that shape inside `.cpu_boot` would
deadlock completion behind the callback's own return.

The current MT6797 admission hooks and P32 rollback publication already sit in
generic CPU-up. They must remain authoritative. A direct `psci_ops.cpu_on()`, a
second timeout, a new completion object, or IPI/DCM continuation at PSCI return
would duplicate ownership and weaken attribution.

The first Buildbox generation attempt from repository commit
`a3176049965bf33d5237355daf0a574b86acf15f` reached the exact prepared source
and stopped before applying an edit. The synthetic parent commit's generic
whitespace check reported three inherited trailing spaces in upstream
`include/linux/cpu.h`. The corrected generator preserves those parent bytes
and skips the generated-diff check only for that initial import; both actual
generated commits, normal patches, and admission still require the check.

The second Buildbox attempt from repository commit
`3feef56ea267ad34cb160ab40ffe07d0b83c3701` passed that import and stopped at
the first source edit because the exact `cpu_operations.cpu_up_rollback`
continuation contains five tabs before its final alignment spaces, while the
generator anchor encoded four. The correction changes only that exact anchor;
no kernel template or lifecycle contract changed.

The third Buildbox attempt from repository commit
`b9c822caa4e148f5bf89f1f367fad992152bd39b` applied the production edits and
reached source validation. It stopped because the validator's general C
definition regex did not recognize the new one-line arm64 dispatcher
signature. Exact token counts replace that ambiguous helper for the two
dispatchers and five split-executor entry points; the generated source is
unchanged.

The fourth Buildbox attempt from repository commit
`08addaa15b4212fdd6ec4e2c452fa46b4515b75e` reached the hook-placement order
check. Its helper used a whole-string search for every token, so both repeated
`if (ret)` guards resolved to the first occurrence and produced a false order
failure. The corrected helper advances a cursor after each match, strengthening
all order checks without changing source or test templates.

## Current conclusion

The bridge contract is frozen. Implementation remains hardware-free and must
pass source, replay, Buildbox, and focused QEMU proof before the roadmap can
advance to the complete binder.

## Follow-up

After this bridge passes, assemble one complete default-off binder around the
proven transition executor, watchdog takeover, retained stage ledger,
platform-effect owner, DA921x provider, BigiDVFS SRAM owner, MT6797 admission
gate, and the two lifecycle callbacks. Do not assemble or write a boot2
candidate until that complete binder passes its own hardware-free proof.
