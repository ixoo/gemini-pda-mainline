# Experiment: checked MT6797 WMT mode negotiation

| Field | Value |
| --- | --- |
| ID | `2026-10-03-mt6797-wmt-negotiate` |
| Status | `in-progress` (kernel integration selected; compile and schema pending) |
| Subsystem | CONSYS / BTIF / STP |
| Device | Project Gemini PDA |
| Investigator | Codex under owner standing authorization |

## Hypothesis and scope

The [successful default exchange](../2026-10-03-mt6797-wmt-default-query/results/runtime-2.json)
permits preparing the next source-matched boundary: a checked mandatory
set-options event, host full-STP reseed, source-matched switch wait and checked
full-mode query including peer credit and host ACK. This compile selection is
not hardware admission. No ROM patch, DLM operation, calibration, WLAN start or
RF scan is selected. A new runtime protocol and validated candidate are still
required before any device effects.

## Selected kernel inputs

Profile `mt6797-a53-wmt-negotiate-compile` extends the active default-query
foundation in canonical series order with three logical format-patches:
the owner/transport caller, its distinct diagnostic binding, and the single
Gemini selector change. The original profile and consumed candidate remain
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
