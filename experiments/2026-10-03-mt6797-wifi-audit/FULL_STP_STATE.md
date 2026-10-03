# Full-mode boundary and one-command transport state

The [state helper](tests/wmt-full-stp-state.h) extends the
[framing codec](FULL_STP.md) with an independently written, one-command window.
The concrete need is the retained pair's 258 patch fragments, four address
commands and two WMT resets: sequence fields must wrap without accepting a
stale event or releasing a command before its transport obligations complete.
It is a host-only draft with no hardware caller or selected kernel profile.

## Selected source boundary

The selected `mtk_wcn_soc_sw_init` completes its mandatory-mode query and
set-options exchanges, sets the host BTIF full-mode flag, enables STP and waits
10 ms before the full-mode query. `wmt_ctrl_stp_conf_ex` maps enable to
`mtk_wcn_stp_enable`; that function resets host context even when enabling an
already enabled transport. Mode selection alone changes the protocol flag.
Thus the full-mode boundary initializes host TX/RX sequences to zero and both
last-ACK values to seven. This is source behavior, not observed peer timing or
an independently established minimum switch delay.

Each patch then uses an ordinary WMT reset command `01 07 01 00 04` and expected
event `02 07 01 00 00`. The script, ordinary WMT TX/RX path and WMT event parser
do not reseed STP sequence state for this event. TX flushes the WMT receive
queue, which is distinct from resetting the STP context. Continue sequence
state across these per-patch resets. The separate STP in-band reset path uses
its own task, resynchronization bytes and pending-reset predicate; it is outside
this helper. Unexpected reset/diagnostic frames retire the proposed lifetime
rather than silently creating a fresh epoch.

## State and integration contract

The helper permits one fully transmitted command at a time. Commit its sent
transition only after every command byte has reached the transport. Received
frames must pass the codec; data must also match the exact expected WMT event
and next receive sequence before any mutation. A peer ACK may accompany that
event or arrive separately before or after it. A repeated last ACK adds no
credit. An ACK outside the current one-command window is refused.

An accepted event advances receive sequence and creates a host ACK obligation.
Mark that obligation complete only after all four ACK bytes are transmitted.
Finish the exchange only after its peer ACK, exact event and host ACK completion;
then the next command can begin. Invalid frames/events/sequences leave state
unchanged. Callers must retire the effect lifetime on a refusal or partial TX,
retain powered resources/evidence and use the reviewed recovery path. Do not
retry merely because the helper remains unchanged.

This intentionally narrows the vendor seven-packet window to one outstanding
command. It supplies no retransmission, timer, frame accumulator, interrupt
synchronization or recovery. The future owner must serialize state changes and
buffer RX arriving during TX, set finite total-frame/time budgets (including
repeated ACKs), and match actual peer ACK timing before hardware admission.
No calibration validator follows from exact fixed-event comparison: calibration
needs its separately reviewed variable-result semantics.

## Focused checks

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/2026-10-03-mt6797-wifi-audit/tests/wmt-full-stp-state-test.c \
  -o /tmp/gemini-wmt-state-test
/tmp/gemini-wmt-state-test
rm /tmp/gemini-wmt-state-test
```

The fixtures exercise 264 successive synthetic exchanges, including repeated
modulo-eight wrap, WMT reset events without reseeding, piggyback/early/late ACKs,
and refusal of premature completion, overlapping commands, invalid ACKs, wrong
status, out-of-order/duplicate events, truncation and event-length mismatch.
Refusal checks verify unchanged state. Strict warnings and address/undefined
behavior sanitizers pass. These test transition rules, not firmware acceptance,
FIFO progress, IRQ races or working Wi-Fi.

The [receipt](results/full-stp-state.json) pins the selected prepared source and
authored files. First [default-query liveness](../2026-10-03-mt6797-wmt-default-query/SESSION.md)
remains required before admitting the mode switch or further device effects.

The [frame-collection follow-up](FULL_STP_STREAM.md) adds bounded byte assembly
and distinguishes software enqueue from hardware FIFO progress. The full
transport owner and its hardware admission remain incomplete.
