# Mainline CPU8 PSCI/generic-hotplug lifecycle bridge

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-27-mainline-a72-hotplug-lifecycle-bridge` |
| Status | hardware-free lifecycle bridge complete; production binding closed |
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
- `templates/` contains independently written source and test snippets.
- `scripts/` deterministically generates, validates, replays, builds, and runs
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

The fifth Buildbox attempt from repository commit
`d4bb33e8aef5eb8154ef5ffc58e7f562694ddee0` passed generic hook placement and
stopped at the injected compatibility wrapper. Its bounded region ended at the
first repeated `true, false, result);` call, which is the secondary handoff,
before the final handoff call. Brace-balanced function extraction now validates
the complete wrapper body; generated source remains unchanged.

The sixth Buildbox attempt from repository commit
`a2292f8a0b235d1d21351e08b15c65d1a5e163b7` passed generation, semantic
validation, and patch creation, then reached strict `checkpatch.pl` review.
It reported no errors or warnings and 20 formatting checks for split function
declarations, calls, and one generated compatibility-test callback. The source
templates and deterministic edit now use aligned arguments without
line-ending open parentheses; lifecycle behavior is unchanged.

The seventh Buildbox attempt from repository commit
`074cbebe73b10702364af24343449fbce86461c3` reduced strict review to one
alignment check: the compatibility wrapper's `request` continuation was one
visual column past its opening parenthesis. Moving that continuation left by
one space is the only source-template change from this attempt.

The eighth Buildbox attempt from repository commit
`1e7a1fc972252d86bd4a95717ce378d698ee9f7e` passed strict review for the
production patch and reached the separate focused KUnit patch. That second
patch had no errors or warnings and 18 call-formatting checks. The test template
now aligns the seven `begin` continuations and keeps the first argument on each
split lifecycle call's opening line; test behavior is unchanged.

## Current conclusion

The lifecycle bridge milestone is complete. Exact Buildbox generation from
repository commit
`07c14f63672a536fb9a312adcb89ba2d03961266` passed production/test source
validation, strict patch review, deterministic replay, and package checksum
verification. The fetched `0394` and `0395` bytes are now admitted to the
canonical series; [the generation record](results/patch-generation-20260827.txt)
pins their identities and invariant counts.

The first exact admitted-tree Buildbox compile from commit
`99f40ac0182c37cf18f60d055af02447cb82a000` passed for release
`7.1.3-gemini-a72-lifecycle-kunit`; all package checksums and the required
lifecycle/test symbols passed. The
[compile record](results/buildbox-compile-99f40ac0.txt) pins the Image,
configuration, System.map, source, and patchset identities.

The exact clean published harness commit
`f69199e31b5a8b7631ab439cbe040cc325e45252` reproduced the same source,
patchset, configuration, Image, and System.map identities on Buildbox. Its sole
bounded no-network QEMU suite passed all ten expected cases with zero failures
or skips before the expected terminal rootfs panic. The
[runtime record](results/kunit-qemu-pass-f69199e3-20260827.txt) pins the runner,
package, raw-log checksum, test names, and result.

The bridge remains hardware-free: there are zero physical backends, MMIO,
retained-RAM writes, SMCs, production callers, physical CPU requests, CPU_OFF
requests, or retries. The MT6797 production callback still vetoes CPU8, no
device action occurred, and no boot candidate was selected.

## Follow-up

Assemble one complete default-off binder around the
proven transition executor, watchdog takeover, retained stage ledger,
platform-effect owner, DA921x provider, BigiDVFS SRAM owner, MT6797 admission
gate, and the two lifecycle callbacks. Do not assemble or write a boot2
candidate until that complete binder passes its own hardware-free proof.
