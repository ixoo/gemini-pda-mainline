# Phase B review 1: runtime-1 failure and the join code

Status: read-only review completed 2026-10-06 on the integrated author tree at
`fae9c7c2723522d83ab34ed0f23f211350370752` (proposals 0135–0140 and their
fixtures) and the runtime-1 build input `a9c1091e…`. No device access.

## Runtime-1 common-init failure

- Proven: no WMT/STP/CONSYS source change since Phase A runtime 3; only the
  WLAN driver changed. The resolved configs differ by the join option and the
  release string; the DTBs are identical.
- Step 5 is the third MCU-clock-raise masked register write, a 20-byte WMT
  payload in a 26-byte full STP frame. `tx=16` is a partial transmission;
  `6/6/5/5` is the link state after step 4's acknowledged exchange.
- Inference, not confirmed: the `-EPROTO` is consistent with the non-initial
  guard in the WMT full I/O refusing an interrupt that arrived with no 0x46
  source pending. The raw IIR was not captured, so the hardware cause is
  unknown. Proposal 0141 addresses that candidate no-source path and makes the
  footer print the IIR; whether it fixes the observed failure is decided only
  by the next runtime.

## Join code findings

1. Behaviour, decided as policy: `mgd_prepare_tx` fails stop on any
   non-admitted prepare, including an auth retry or an unexpected disconnect.
   The first admission keeps that deliberately; it is stated in the README.
2. Bug, fixed by 0142: `join_internal` dangled after the failure and close
   paths freed the driver-built deauthentication frame through
   `ieee80211_free_txskb`.
3. Latency, not fixed: `schedule_delayed_work(…, 0)` does not expedite a poll
   already queued for 20 ms. Not a blocker for the current margins.
4. Accepted: a failing packet drops the whole RX batch, consistent with
   fail-stop.

## Checked and found correct

The management TX descriptor fields and page accounting; TX done kept
separate from credit return; the lock order (the waits drop the MAC mutex;
`ieee80211_rx_ni` and `ieee80211_tx_status_ni` run outside driver locks;
`.tx` is atomic-safe); and the EAPOL decoder's bounds and layout checks. One
runtime uncertainty remains: the translated-Ethernet EAPOL path assumes an RX
descriptor group-4 layout not yet confirmed on hardware.

## Tests

The peer fixture stubbed `join_close`, so teardown ownership was untested.
`tests/run-ownership-test.py` now exercises the production worker and close
paths; `tests/run-wmt-irq-test.py` exercises the production WMT full I/O
header for the no-source interrupt cases.
