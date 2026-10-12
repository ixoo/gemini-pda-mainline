# Runtime 34 result — two-lifetime station re-arm (candidate 33)

One reviewed run, one reviewed recovery, no retry. Root is the sole device
custodian; this records the run truthfully, including its limits.

## Identity and recovery

- Execution source: commit `624e16a4`; the leaf-wait cleanup tests (`172fdba4`)
  passed independently and the runtime scripts were byte-unchanged from `624e16a4`.
- Candidate: C33 — build commit `6d6eabeb`, package `01851`, built on the C32
  parent; full identity in the committed receipt
  `results/candidate-33.json` (sha256 `064d0f81b644eb2409406fa46054fa5ac135117bcf08678215466aaebebb4a37`).
- Mainline boot: `c3c13385-7138-493e-b7df-6fe5673c6739`. Recovery returned to
  fresh Gemian (boot `777dd6a6`), confirmed `3.18.41+` / aarch64. One reviewed
  recovery only.

## Evidence integrity

All 63 pre-recovery sealed files hash-match. The boot-bound quiescence record is
boot-matched with an empty faults line; the Wi-Fi helper process group was
confirmed gone/safe; the supplicant log exported complete (33426 B). Cycle 1's
per-cycle archive was retained. Cycle 2 had no data directory (its lifetime
failed early), so the per-cycle export's `complete=false` is an expected negative,
not a transport loss.

## What the two lifetimes showed

Both scans completed (frame/beacon/credit accounting, retired=1, each with
tuning 4/4 and pending 0).

- First lifetime: a full healthy data join — WPA2 association, DHCP (exit 0,
  bound 1, /24 prefix), ping 3/3, a fresh post-join Wi-Fi SSH exchange (exit 0 +
  host-ack), and a healthy cleanup and re-arm.
- Second lifetime: the scan succeeded. Its owned-bss-notification handler observed
  and admitted two notifications during scan 2 —
  `bss=0 is_absent=1 quota=2 reserved=0 scan_active=1 count=0`, then
  `bss=0 is_absent=0 quota=0 reserved=0 scan_active=1 count=1` — so the proposal
  0182 predicate was exercised, and 0183's per-scan tuning reset ran (4/4 each
  scan). The JOIN then refused a LATER control event — 12 bytes, le16 type
  `0xe000`, id `0x11`, seq 0, taking the `-71` branch 6 — and no management, key
  or data submissions followed. The second lifetime therefore did not complete a
  data join.

**Two-lifetime verdict: negative.** Exactly one lifetime completed the full data
path; the two-lifetime re-arm did not achieve a second complete data join.

## Limits — what this run does NOT establish

- The LATER refused JOIN control event's body was NOT logged; its payload and
  freshness are unknown and are not inferred here. Neither admitted scan-2
  notification body is assigned to it — they belong to the scan handler, a
  different phase and ownership.
- The join-path refused event and the scan-admitted notifications are the SAME
  firmware event/ABI (EVENT_ID_BSS_ABSENCE_PRESENCE, le16==`0xe000`, id `0x11`),
  routed through different phase handlers — the scan handler admitted it in scan
  2; the join phase refused it. Only the unobserved third payload/context is
  distinct, not the event identity.
- 0182 was exercised and 0183's reset observed in scan 2 (above); this run does
  not, however, establish the join-path event's correct handling — that is the
  open gap below.

## Follow-up (no new build)

The join-path known-event refusal is a gap to assess against the actual current
phase/ownership and the source event handler, not a payload to infer. The admitted scan-2 notifications are recorded in the private supplemental
file `scan-notification-metadata.txt` (sha `68baebea`), preserved with the
original six-file handoff; it is not copied into the repository. OpenCode
receives the same results to advise. No new kernel build until a specific
correction or measurement is reviewed.
