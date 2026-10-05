# Experiment: MT6797 Bluetooth H1 positive control

| Field | Value |
| --- | --- |
| ID | `2026-10-05-mt6797-bt-h1` |
| Status | Driver draft; host and schema checks pass; runtime untested |
| Profile | `mt6797-a53-stp-task-routing-compile` |
| Subsystem | MT6797 CONSYS WMT and STP task 0 |
| Date | 2026-10-05 |
| Device action | None |

## Purpose

This is roadmap offline item 2, the smallest task-0 Bluetooth path for C3.
It answers hypotheses H1, H2 and H5 from the
[Bluetooth record](../2026-10-04-gemini-bluetooth-re/README.md) in one boot.
H6 was answered separately by a Gemian read; see that record.

## Changes

Four experiment-only patches extend the STP task-routing profile:

- [0107](../../patches/proposals/0107-soc-mediatek-select-the-task-of-one-full-STP-exchange.patch)
  gives the one-command full-STP exchange a task, WMT or Bluetooth, and an
  exact reply prefix with a fixed total length. The receive stream refuses
  data for any other task. WMT callers keep their exact whole-event match.
- [0108](../../patches/proposals/0108-dt-bindings-soc-mediatek-mt6797-consys-add-one-shot-BT-reset.patch)
  adds `vcn33-bt-supply` and the `mediatek,one-shot-bt-reset` flag to the
  CONSYS binding. The flag requires the negotiation flag and the supply.
- [0109](../../patches/proposals/0109-soc-mediatek-add-a-one-shot-MT6797-Bluetooth-positive-control.patch)
  runs the sequence after a successful negotiation, in the same root trigger.
- [0110](../../patches/proposals/0110-arm64-dts-mediatek-gemini-describe-the-VCN33-BT-supply.patch)
  describes VCN33-BT on the board. The flag itself stays out of the board
  file; a candidate adds it.

The sequence enables VCN33-BT at 3.3 V, then runs five exchanges on the
negotiated link:

| Step | Task | Command | Accepted reply |
| --- | --- | --- | --- |
| BT on | WMT | `01 06 02 00 00 01` | exactly `02 06 01 00 00` |
| HCI Reset | BT | `01 03 0c 00` | exactly `04 0e 04 01 03 0c 00` |
| Read Local Version | BT | `01 01 10 00` | 15 bytes starting `04 0e 0c 01 01 10 00` |
| Read BD_ADDR | BT | `01 09 10 00` | 13 bytes starting `04 0e 0a 01 09 10 00` |
| BT off | WMT | `01 06 02 00 00 00` | exactly `02 06 01 00 00` |

Each exchange has a 600 ms deadline inside a 3 s budget. The first failure
stops the sequence and keeps power, clocks and the rail for reviewed recovery.
VCN33-BT is switched off only after a successful BT off. No ROM patch,
calibration, sleep, wake or radio setting command is sent, and no HCI device
is registered. The raw bytes go only to the private sealed session log; the
address is a device identifier.

H5 needs no extra command. If the chip were to sleep between exchanges, a
later step would time out, and that is recorded as the failing step.
H3 and H4 are not tested here.

## Decision branches

- **All five steps pass.** H1 and H2 hold. Bluetooth transport work can
  proceed without the ROM patch, and task 0 is a positive control for GNSS.
- **BT on passes, HCI Reset fails.** Inspect the raw bytes and link state for
  a task-delivery or sequencing problem before another boot.
- **BT on fails.** BT on needs the patched image; H1 is false and Bluetooth
  waits behind common init.

## Validation

[test-bt-h1.c](test-bt-h1.c) compiles the actual link, state and stream
headers with ASan and UBSan. It checks task filtering in the stream, prefix
matching with a captured tail, refusal of the wrong task, wrong prefix and
wrong length without changing link state, duplicate refusal, and sequence
continuity from a WMT exchange into a task-0 exchange.

```sh
d=$(mktemp -d); cp PREPARED/drivers/soc/mediatek/{stp-full,stp-full-link,stp-full-task,wmt-full-stp,wmt-full-stp-state,wmt-full-stp-stream}.h "$d"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -I"$d" test-bt-h1.c -o "$d/t" && "$d/t"
```

The twelve existing fixtures from the
[task-routing runner](../2026-10-04-mt6797-stp-task-routing/test-tasks.py)
pass against the modified headers. On this host the sanitizer builds need
`setarch "$(uname -m)" -R`; with full address randomization one fixture
spins indefinitely, while the same fixture without sanitizers passes.

All four patches pass strict checkpatch, excluding only the missing
sign-off, the new temporary header's maintainer entry and the inherited
`acknowledgement` spelling. The updated binding passes `dt-doc-validate`.
The board DT validates against it, and the flag is rejected without the
negotiation flag or without the supply.
