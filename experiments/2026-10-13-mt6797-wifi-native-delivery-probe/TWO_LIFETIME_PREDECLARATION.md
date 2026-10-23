# Two protected lifetimes — incomplete offline admission

The same-firmware route has since resolved negatively. See the [firmware-restart prerequisite audit](FIRMWARE_RESTART_BOUNDARY.md); it has UNKNOWN items and no restart run has been predeclared. The procedure below is historical and unadmitted.

The owner accepted this hold. The active [two-track work list and decision](TWO_LIFETIME_OFFLINE_TRACKS.md) now permit dormant host prerequisites only; all build and boot work remains held.

Owner request, 2026-10-23: two lifetimes in one boot, 120 seconds each, then
firmware stop and reviewed return. No P2E run, repetition, sampler, firmware
command extension or limit extension. P2E-D1/D2 remain consumed; their 600-second
traffic, transmitted delivery and whole-ledger result stand separately.

**Current decision: HOLD before build.** The actual-source attribution fixture
reproduces the counterexamples below. No second-lifetime capability is enabled,
no candidate exists, and no boot allowance has been consumed. This is an
incomplete offline checkpoint, not the requested two-lifetime delivery.

The installed kernel is `3da69187`; it lacks proposal 0228. A new kernel build
is mandatory for any eventual candidate. Canonical `patches/series` and the
snapshot compile profile select 0228 after 0227, but this work has not built
that profile or established a compile result. No installation or physical boot2
selection is pending.

## Offline gate result

The [actual-source fixture](tests/second-lifetime-attribution-test.py) extracts
the complete key-event branch from the public MAC source through 0228 and uses
the maintained PTK/GTK checkers and descriptor builders. The kernel environment
is stubbed; production event predicates, state updates, completion publication
and PN checks are compiled unchanged with ASan/UBSan.

| Boundary | Actual result | Consequence |
| --- | --- | --- |
| Key event before a new install | Refused; no completion published | Existing window refusal works. |
| Same event during a new pairwise install, assuming re-arm was enabled | Byte-identical old event sets `join_key_done` and completes `ccmp_key_done` | A new host generation cannot establish provenance for this untagged event. |
| Same event after pairwise installation, during group installation | Counts as the second key event | BSS/peer matching and window counts do not identify key index or incarnation. |
| Old TX completion with a distinct new wire PID | Refused | Fresh wire ownership can discriminate this case. Reusing the same PID cannot gain provenance from a host generation alone. |
| Old PTK/GTK RX descriptor with PN 100 and a fresh host context | Accepted by the actual checker | A fresh generation/context cannot establish which key produced already decrypted data. This is a counterfactual reuse test, not observed firmware leakage. |
| Equal/lower PN or mismatched GTK index | Refused; existing checks preserved | These checks remain necessary but do not resolve key incarnation. |
| New-key PN 1 with the old PTK floor retained | Refused | Carrying the old floor forward is not a valid replacement for retirement. |

Production stable-CCMP still forbids re-arm, so the counterfactual install
states above are not reachable through a newly enabled production path.
No fatal/poison path was changed. A passing diagnostic means the missing
contract was reproduced, **not** that second-lifetime admission passed.

The concrete missing boundary is evidence that the existing teardown retires
old key notifications and firmware/HIF queued data before a reused key/peer/BSS
can admit them, or an existing supported resource identity that distinguishes
those old producers. Key/station removal credits establish command-buffer
consumption; they are not an acknowledged data/event purge. The production
cleanup source states this distinction explicitly. Stage 3 and a whole ledger
alone do not prove that boundary. Management-class queued-frame release does
not establish data-frame retirement.

Do not substitute key-state value 2 for a per-operation acknowledgement: it is
set after removal submission. Later serialized credit reconciliation is
necessary to complete cleanup, but neither that state value nor the global
ledger is an event-generation token. An implementation also still needs the
explicit removal-credit, quarantine, reserved-owner and pending CPU/FFA gates
requested by the owner; no claim is made that the legacy re-arm helper already
implements them.

The source-supported retirement/attribution boundary must be resolved before
wiring re-arm, generation-owned operations or fresh per-key PN contexts into
protected reuse. Dormant, unconsumed helpers are now permitted under the active
two-track work list.
Refusing all second lifetimes would preserve safety but would not implement
the requested capability. No always-refusing substitute candidate is selected.

## Conditional one-boot procedure — not build-ready

After offline admission passes, commit and push the complete source, fixtures,
profile and host procedure. Build from a clean checkout with
`./scripts/build-kernel --backend buildbox`, including 0228. Confirm the
snapshot compile profile also builds; validate package provenance and artifact
identity. Install only that candidate with the reviewed boot2 guard and matching
full-partition readback, shut down cleanly, and stop for the owner's physical
boot2 selection. Verify changed boot identity, exact kernel/config/root and
active logger before firmware start. No consumed receipt or handoff is reused.

Each lifetime then performs one join, DHCP, three pings and at least 120 seconds
of authenticated received SSH traffic. Use one EOS-derived standard disconnect
per lifetime, require whole-ledger stage 3, and preserve a generation-bound
delivery verdict and cleanup result. The 120-second host recipe and its window
arithmetic must have actual offline fixtures before build; the existing window
derivation requires a 600-second endpoint and is not directly reusable as a
120-second admission. No host/driver/resource limit is extended.

| First outcome | Required decision |
| --- | --- |
| Lifetime 2 admission refused | Record exact missing barrier and stop; no in-boot retry. |
| Lifetime 2 joins but carries no traffic | Record key/ownership result and stop. |
| Either standard disconnect refused | Record harness result and stop; do not repeat control. |
| Any first error, credit anomaly or link loss | Stop, export evidence, verify quiescence, then use reviewed return. |
| Both lifetimes complete | Require firmware stop, sealed export and reviewed return; confirm changed-boot Gemian. |

The delivered evidence must identify the candidate and boot and contain a row
for each lifetime: admitted/refused with reason, traffic result, exact reserved
completion status, delivery verdict, cleanup stage/ledger/debt and removal-credit
outcomes. No runtime rows are invented for this offline hold. Even two successful
bounded lifetimes would establish only that reconnect milestone on the tested
path; they would not establish general rekey, arbitrary reconnect or maintained
Wi-Fi support. **The reconnect goal remains open.**
