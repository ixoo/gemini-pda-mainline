# Experiment: bounded pre-patch WMT chip reply capture

| Field | Value |
| --- | --- |
| ID | `2026-10-03-mt6797-wmt-identity-capture` |
| Status | candidate and tooling validated offline; deployment/runtime pending |
| Subsystem | MT6797 CONSYS, BTIF and WMT |
| Device | Project Gemini PDA |
| Profile | `mt6797-a53-wmt-identity-capture-compile` |

The [ROM applicability review](../2026-10-03-mt6797-wifi-audit/ROM_APPLICABILITY.md)
found an inconsistent vendor read-event length and unchecked ROM-read returns.
This diagnostic measures the pre-patch chip reply without selecting firmware.
The [capture leaf](../2026-10-03-mt6797-wifi-audit/IDENTITY_CAPTURE.md) sends one
26-byte mandatory-STP read, retains up to 32 raw bytes, and stops by its
500-ms/64-service limits. Deadline expiry is not identity acceptance.

## Selected caller and boundary

Proposals 0096–0098 add the caller, binding and board selection after the proved
negotiation foundation. The default-off property is
`mediatek,one-shot-wmt-identity-capture`; it excludes both existing WMT selectors.
Its sole root trigger is `wmt_identity_capture`, after the existing exact WMT
memory preparation and deferred-start prepower gates. The shared CONSYS mutex
and consumed deferred-start flag own the lifetime.

The existing BTIF setup is factored from the default-query function without
changing its pretrigger statements. The capture calls setup directly, then the
bounded leaf. It sends no default query or negotiation command first. Raw TX/RX
and terminal counters are logged from persistent storage after IRQ retirement;
there is no added hardware observation for logging. The selected diagnostic
sets the existing query-only continuation guard, so HIF, EMI-set/copy, WLAN
firmware start and scan are not executed after reset release. WLAN stays disabled
in the board DT. Power and clocks remain retained for reviewed recovery.

[Integration validation](results/integration.json) records exact scoped patch
replay, strict Checkpatch, query/setup regression and capture/negotiation
fixtures. These prove neither Linux compilation nor actual resource admission,
FIFO progress or reply encoding. The selected input must compile and pass
focused binding/DT checks on Buildbox before candidate construction. No runtime
protocol, candidate or installation is admitted by this checkpoint.

Build only from clean pushed inputs:

```sh
KERNEL_PROFILE=mt6797-a53-wmt-identity-capture-compile \
  ./scripts/build-kernel --backend buildbox
```

A future boot must distinguish the pre-patch chip response, retain complete
private evidence and return through reviewed recovery. No HW/ROM read, patch,
PA/calibration or WLAN continuation follows from the capture. Working Wi-Fi
still requires checked common initialization, management reception, association
and traffic; this experiment resolves one prerequisite.

## Build and schema follow-up

[Build 1](results/build-1.json) now records the exact compiled/fetched package
and clean pushed input. The [schema checks](results/schema-1.json) validate its
exact board DTB, reject seven invalid resource/selector variants and retain
both earlier selector variants. Two existing USB `ranges_format` warnings
remain outside the selected CONSYS scope. The independent schema output DTB
matches the package digest. Candidate composition and its reproduction oracle,
finite runtime protocol, guarded deployment and actual reply capture remain
unproved; this is not Wi-Fi support.

## Candidate and runtime preparation

The [candidate receipt](results/candidate.json) and
[tooling validation](results/tooling-validation.json) now pin two identical
constructions, the composed-DTB schema check, actual-candidate refusal checks
and focused evidence/restoration fixtures. The [runtime protocol](RUNTIME_PROTOCOL.md)
selects one chip read before negotiation with finite effects and mandatory
preservation/recovery. No deployment or measured chip identity is claimed.

Use the private repository root through `GEMINI_PRIVATE_REPO`. The installer
binds the reviewed device guard; capture and passive-host preparation require
its actual deployment receipt. `passive-session.py` can validate the inherited
private RAM root offline without claiming deployment. No new kernel build is
needed for these host-only tools; the selected kernel inputs remain `8956fbc1`.
