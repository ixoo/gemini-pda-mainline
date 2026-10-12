# Runtime 32 result: second complete bounded C2+C3 pass; the group-1 observation present and consistent — every sampled delivered frame carried GROUP_VLD 0x8 (no group 1)

Boot: mainline `869f4bdf-1f54-48d3-8076-224f4910f80e`, release
`7.1.3-gemini-a53-wifi-phase-b-compile`, on candidate 31 (compile 36, package `521e1ce3…`,
built input 7fa36c01, full padded boot2 `54791b43…`), session tools at 21066579, consumed
once by the custodian after deployment 31 (generated installer `ffadf589…`, predecessor
installed candidate 30 `e758bf36…`, guarded live GPT, clean shutdown; the owner selected
boot2 physically). Evidence: the custodian's thirteen sanitized uploads in the ignored
private evidence directory (mode 0700, each file 0600, every hop SHA verified; 48 seal
manifest members); kernel log sealed complete (167191 bytes, 2104 records, SHA-256
`501a2eb3…`, coverage sequence-zero-through-seal); supplicant log complete (26364 bytes,
SHA-256 `d3de9575…`, 0 residual processes, boot match, independently framed); logger
94742 ms; the host wait ended on the join's terminal (exit 0, host phase 9.376 s, empty
keepalive, stderr 0). No raw capture, packet content, address, credential or image is
published.

## Verdict (as computed, preserved)

The second complete bounded C2+C3 pass: `c2_session_pass=true`, `c3_session_pass=true`,
`bounded_join_pass=true`, `healthy_cleanup_demonstrated=true`,
`stage_and_credit_order_verified=true`, both driver paths true, no refusal
(`refusal_recorded=false`), no terminal failure, not malformed
(`malformed_stage_record=false`). `wifi_operational=false`. One bounded lifetime, not an
operational, reliability or replay-protection claim.

## The group-1 (received PN group) observation — present and consistent

The required `data group1` observation line is present and the classifier marks it
consistent: `uni_present=0 uni_absent=33 grp_present=0 grp_absent=27 uni_masks=0x100
grp_masks=0x100` (sequence 2085, immediately after the data phase end record and before the
cleanup submissions). Its `present + absent` reconcile exactly to the end record's delivered
counts (33 unicast, 27 group); each per-class mask bitmap is `0x100`, i.e. only mask value 8
was seen — **every one of the 60 delivered frames carried GROUP_VLD `0x8`, group 4 only, with
group 1 (the received PN group) absent**. The first data RX record agrees:
`group=1 tid=0 keyid=1 bytes=46 vector=0 group_vld=0x8`.

What this does and does not mean. On this one lifetime no delivered frame of either class
carried a group-1 PN. This is **not** proof that the firmware never attaches group 1 (one
sample, one AP, one session), **not** a replay-protection statement, and **not** a reason to
treat the crypto/replay boundary as satisfied: a received PN was simply not present to
consider, so the standard-mac80211 and host-rx_pn options both remain unexercised, and the
crypto boundary stays a separate, required, unmet condition. The absence of group 1 here does
not justify shipping with that gap or adopting a generic replay floor.

## Observed (kernel records, µs since boot; chronology from the sanitized join-records, record SHA `53715071…`)

- Handshake and keys as in runtime 31: open-system authentication, association, the two
  EAPOL deliveries with activation, both key commands submitted and credited
  (`key done: first after=pairwise`, `key credit returned: pairwise`; `second after=group`,
  `key credit returned: group`). The supplicant log carries the matching four-way messages,
  `installing ptk`/`installing gtk`, `key negotiation completed`, exit 0, 0 processes.
- Data phase: opened at sequence 2037 (88994049) with `budget_ms=6168 teardown_margin_ms=5000
  inside_grant=1` — the grant is held through the data phase (returned at cleanup stage 1),
  per the driver's `release_channel`; ended at sequence 2084 (95174576)
  `reason=budget elapsed_ms=6180 rx_unicast=33 rx_group=27 rx_dropped=0 tx_queued=28
  tx_done=28 tx_failed=0 tx_credits=57`. The 28 TX completions are status-0 completion
  records, not a measured ACK or delivery proof, and are not split by Ethernet unicast.
- Beacons: four delivered records, total at stage 3 `beacons delivered: total=64 keyed=61`.
- Discards, all pre-existing classes: three pre-key `group data discarded` records (sequence
  2015–2017, the 0164 class — status 0xc004, sec 0, broadcast match, WLAN index 2, bss 1,
  frame control 0x6208/0x6208/0x4208, before the pairwise key submission at sequence 2029),
  six `group action frame discarded` (status 0xe000) and one directed `action frame
  discarded`. The new **0178 data LLC-mismatch class (status 0xc200) was not observed**
  (`data_llc_discards` 0, total null) and the **0177 cleanup class was not observed**
  (`cleanup_group_discards` 0, total null); neither is demonstrated.
- Cleanup, healthy: deauthentication, both key removals credited, cleanup submissions 0–2,
  and the healthy `cleanup: stage=3 credits=returned slots=retired deauth=1` at sequence 2101.
  No footer followed.
- Host, separately: `udhcpc` exit 0, one lease bound, prefix 24; `ping` 3 sent, 3 received;
  the laptop's one Wi-Fi SSH exchange exit 0, 37 bytes, boot match true, readiness after
  6.7 s, elapsed 8.0 s, bound to `mainline_boot` `869f4bdf…`. The milestone repeated; none of
  it is an operational or reliability claim.
- Supplicant disconnect: one event, reason 4, `locally_generated=1`, line 372 (1-based; the
  log has no per-line timestamps). As in runtime 31, the kernel data phase ended on its
  budget and the cleanup completed healthy; the single local disconnect is a field, not a
  cause.

## Recovery (as computed, preserved; the request-stage field is not rewritten)

The reviewed native recovery was requested once after the seals: `native-request-result.json`
records `recovery_confirmed=false` — the request-stage field. The return collector then
recorded the completed return separately (`recovery_confirmed=true`, 3 attempts, elapsed
30.756 s, classification `changed-ID-Gemian`), and an independent known-good Gemian SSH
confirmed the changed boot `32144a9b-6a7a-4840-becb-e03bf667afb5`, release 3.18.41+, aarch64.
The device is on Gemian now. Both the request-stage `false` and the confirmed `true` are kept
as recorded.

## What this establishes

Twice now, the full mainline WPA2-PSK station lifecycle runs cleanly as one bounded lifetime
and tears down healthy. The new measurement answers its one question for this sample: group 1
(the received PN group) was present on no delivered frame — an availability fact, not a
replay, enforcement or operational claim, and not grounds to treat the crypto boundary as
met. The next step is a design question (the smallest coherent reusable healthy lifecycle),
recorded in [REUSABLE_LIFECYCLE_DESIGN.md](REUSABLE_LIFECYCLE_DESIGN.md), with the crypto/replay
boundary a separate required condition. No identical boot is repeated; no new kernel build is
implied by this record.
