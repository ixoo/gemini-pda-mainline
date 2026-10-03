# Experiment: checked MT6797 WMT mode negotiation

| Field | Value |
| --- | --- |
| ID | `2026-10-03-mt6797-wmt-negotiate` |
| Status | `completed` (bounded negotiation passed; working Wi-Fi remains incomplete) |
| Subsystem | CONSYS / BTIF / STP |
| Device | Project Gemini PDA |
| Investigator | Codex under owner standing authorization |

## Hypothesis and scope

The [successful default exchange](../2026-10-03-mt6797-wmt-default-query/results/runtime-2.json)
permits preparing the next source-matched boundary: a checked mandatory
set-options event, host full-STP reseed, source-matched switch wait and checked
full-mode query including peer credit and host ACK. This compile selection is
not hardware admission. No ROM patch, DLM operation, calibration, WLAN start or
RF scan is selected. The selected candidate, runtime protocol and verified deployment below
attribute the completed single device test.

## Selected kernel inputs

Profile `mt6797-a53-wmt-negotiate-compile` extends the active default-query
foundation in canonical series order with logical format-patches:
the owner/transport caller, its distinct diagnostic binding, and the single
Gemini selector change, followed by bounded private wire-evidence export. The original profile and consumed candidate remain
unchanged. The new release is `7.1.3-gemini-a53-wmt-negotiate`; DEBUG_FS is
inherited for the existing pre-trigger CCF prerequisite. WLAN remains disabled.

The distinct `mediatek,one-shot-wmt-negotiate` property creates only the deferred
`wmt_negotiate` root trigger. It is mutually exclusive with the default-query
selector and retains the exact nine resources, clock handles and sysirq route.
One CONSYS owner holds the shared lock across all phases and retains separate
persistent command records and powered resources on every result. Phase,
counts and STP/ACK state are logged. No negotiation runs automatically at probe.

The [caller review](../2026-10-03-mt6797-wifi-audit/NEGOTIATION_OWNER.md) and
[IRQ/FIFO review](../2026-10-03-mt6797-wifi-audit/FULL_STP_IO.md) own transport
contracts and host-fixture limitations. The [input receipt](results/integration.json)
pins exported bytes and distinguishes those checks from Linux/hardware validation.

## Build and remaining gates

```sh
KERNEL_PROFILE=mt6797-a53-wmt-negotiate-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-wmt-negotiate-compile ./scripts/buildbox fetch-package
```

Use a clean pushed checkout. Validate the exact package, focused binding/board
schema and source integration before composing a candidate. Then review the
new effects, finite budgets, preflight, success/failure evidence and native
recovery protocol. Only that validated candidate may be installed for a fresh
owner-selected boot. Successful negotiation permits common-init preparation;
it does not prove ROM patch applicability, calibration or working Wi-Fi.

## First compile and evidence follow-up

[Build 1](results/build-1.json) passed Buildbox compile and validated remote/local
package checks. [Schema 1](results/schema-1.json) passed the selected binding,
exact package-matching board node, required-resource mutations, selector
exclusion and compatibility with the consumed default-query board. Existing USB
ranges warnings remain outside this focused binding scope.

The first caller logged counts but kept raw reply bytes only in owner memory.
The [selected follow-up](results/wire-evidence-inputs.json) retains malformed
initial-query input and exports bounded per-phase TX/RX bytes into the private
complete kernel log before recovery. It performs no additional device reads.
[Build 2](results/build-2.json) compiled the exact follow-up and passed package validation.
The binding and compiled board DTB are byte-identical to Schema 1, so those
focused checks remain applicable. Candidate and runtime protocol preparation
followed before the completed device test. Raw bytes,
firmware and private logs must not be published with sanitized runtime receipts.

## Candidate and runtime packet

[Candidate](results/candidate.json) was reconstructed twice with identical bytes;
only the RAM-root release gate and selected transport owner/WLAN nodes change
from the proven foundation. [Validation](results/tooling-validation.json) covers
actual guard/trigger fixtures, private wire classification, exact candidate
preparation, and generated installer/trigger shell checks.

The [runtime protocol](RUNTIME_PROTOCOL.md) and [session packet](SESSION.md)
select one new negotiation lifetime and preservation/recovery on every outcome.
[Deployment 1](results/deployment-1.json) passed live guards, full readback and
clean shutdown. Runtime 1 below records the consumed negotiation lifetime.

## Runtime result

[Runtime 1](results/runtime-1.json) establishes the checked mandatory default and
set events, full-STP options event, peer credit and transmitted host ACK. Full RX
contained a peer ACK followed by the matching event. Complete sealed-log
preservation, A53 regression and changed-boot Gemian recovery passed.

The original offline classifier rejected the admitted CONSYS power/reset log
records as WLAN continuation. [Review](results/classifier-review.json) confirms
the exact compiled owner returns before HIF/WLAN continuation; corrected fixtures
accept those prerequisite records while still rejecting WLAN/HIF/EMI actions.
Reclassification used the unchanged sealed log; no hardware retry occurred.

This closes the negotiation boundary only. ROM applicability, remaining common
initialization, calibration and Wi-Fi reception are still open. The consumed
candidate is not selected for another boot.
