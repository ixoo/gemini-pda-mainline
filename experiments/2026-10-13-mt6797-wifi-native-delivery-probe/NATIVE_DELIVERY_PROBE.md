# Native-crypto-delivery diagnostic (proposal 0181, default-off, bounded hybrid)

Admitted for authoring only; **no build, device or radio action here.** A separately
profiled, default-off driver diagnostic that tests one question: does a firmware mode deliver
intact **protected native MPDUs** the host can authenticate through standard mac80211 — the
route-4 precondition for maintained RX crypto. Ciphertext availability and station/monitor
coexistence are the **runtime hypothesis**, not a precondition. The admitted candidate 32 /
runtime 33 (compile 37) are unchanged; a diagnostic result is not driver completion.

## Parent / provenance

Authored on the exact reviewed parent: c2c3 `d484b4d6` = proposal 0180 (the two-lifetime
re-arm = the compile-37 kernel, `5d6323e1`/`b33ba5a2` inputs). 0180 touched only
`join-rearm.h` + `mac.c`, not `join-commands.h`/`data-rx.h`, so the RE code-reading contexts
are unchanged. 0181 is a successor commit on 0180; it is added to the canonical
`patches/series` in order (after 0180) and selected **only** by the new profile
`series-a53-wifi-native-delivery-diag` (compile-37 selection + 0181). The compile-37 profile
series is untouched. `scripts/validate-manifest-series` and the invariant test pass; pinned
`checkpatch.pl` on the patch shows only the standing archive-proposal exceptions
(no Signed-off-by, new-file MAINTAINERS note).

## The command (source-grounded)

`CMD_ID_SET_MONITOR = 0xFC`, the 16-byte `CMD_MONITOR_SET_INFO_T` encoded by
`mt6797_native_monitor_payload` (join-commands.h): the **seven exercised field values** of the
retained caller `priv_driver_set_monitor` (gl_wext_priv.c:2865) — band 0, primary 40,
SCO/width/S1/S2 0 — with the reserved bytes **deterministically zeroed**. That is a match on
the exercised fields plus explicit reserved-zero, **not** a literal match to the caller's
unspecified stack reserved bytes (wlanoidSetMonitor does not initialise them); the firmware
body reads neither the band byte nor the reserved bytes. Only channel 40 is admitted; the host
monitor-netdev policy (`monWork`/`kalSetMonitor`) is deliberately not used.

## Strict native RX decoder (`mt6797_data_rx_native`, data-rx.h)

Reuses the source RXD walk (nicRxFillRFB nic_rx.c:300-345): offset = 16 + the present status
groups in **4/1/2/3 order** + the BIT(6) header-offset pad; `u2PacketLen = count − offset`,
delivered verbatim. Native-class gates, derived (not copied from the translated class):

- **Header translation OFF** (`ucHeaderLen` BIT7 clear) is the native gate; Group 4's presence
  is **not** — a present Group 4 is skipped by its size, never used to rebuild the header.
- **MSDU0** (`ucBssid` payload-format bits 0..1 == 0): no deaggregated AMSDU sub-frame.
- The original 802.11 MPDU at the post-group offset is a protected **data** frame
  (version 0, type data, Protected, FromDS and not ToDS), **no** More Fragments, fragment
  number 0, **no** Order/+HTC, subtype data(24-byte) or QoS-data(26-byte) with the reported
  header length matching; `addr2` (TA/BSSID) == the AP, `addr1` == own (unicast) or group.
- **CCMP-shaped** eligibility (not proven CCMP until the standard AEAD): CCMP header reserved
  byte 2 == 0, Ext-IV set, reserved low 5 bits of byte 3 clear.
- Conservative, **clearly-labeled** bad-FCS filter (`u2StatusFlag` bit 1): a reported bad FCS
  does not logically preclude a valid MIC, so it is a metadata filter, not an auth decision;
  no tail-FCS byte is stripped.

The accepted frame is the **untouched** MPDU (IV and MIC preserved). Every translated, plain,
non-CCMP, non-peer, legacy, short or unknown shape is **withheld** (inconclusive), never
guessed or corrected live. `authentication` comes from the original protected MPDU through
standard mac80211's CCMP AEAD/MIC + replay check, not from descriptor metadata.

## mac.c integration — asynchronous, never blocks the worker

The control runs inside `join_work`; it must never block on its own ledger (a worker waiting
for itself would time out). A compact **asynchronous** state machine (pure
`mt6797_native_diag_transition`, native-diag.h) is stepped once per worker iteration
(`mt6797_native_diag_step`): IDLE → (armed, healthy data phase, ledger quiescent) submit one
enable → ENABLE_PENDING → (the enable's page/credit retires on a later iteration through the
shared credit/page ledger, as the in-worker commands reconcile) ACTIVE → (a ceiling reached)
submit one disable → DISABLE_PENDING → (retires) CLOSED. Each submit charges exactly one page
with a credit deadline (the existing `join_credit_pending`/`join_page_debt` pattern); nothing
blocks. On a command deadline or any poison the machine **latches the no-radio stop**
(`first_error` + `closing`) **before** any submission path — and the existing submission
guards (`mac_send`, `join_retire_idle_bss`) already honour `first_error`, so no redundant guard
is added. HIF stays opaque (no MAC pointer in hif.c).

- **Central ALL-RX accounting**: immediately after each frame is read, before any class
  dispatch, every frame and all its logical bytes are counted while the window is pending or
  active (SW events, management and data alike). Delivery is prospective — `mt6797_native_diag_admit`
  delivers only in ACTIVE and only while no ceiling is reached.
- **Delivery**: an admitted frame that the strict `mt6797_data_rx_native` accepts is delivered
  as the untouched MPDU with `mt6797_native_diag_ordinary_flags()` — **all** crypto bypass/strip
  flags clear (DECRYPTED/IV_STRIPPED/PN_VALIDATED/MMIC_STRIPPED/MIC_STRIPPED, ALLOW_SAME_PN left
  clear), no 802.3. The translated path is withheld whenever the window is engaged; ordinary data
  **TX is fenced** while an enable/disable is pending.
- **Bounds** (native-diag.h, pure): 10 s wall, 512 total RX frames, 64 native frames, 1 MiB
  total RX bytes; the wall is enforced even on an empty RX stream by tightening the data-phase
  deadline when the window becomes active; the lower existing data-phase ceilings also stop it.
- **No-radio proof (V21-confirmed)**: once a latch sets `first_error`/`closing`, the pure
  transition returns **no** SUBMIT action in **any** state (unit-tested across all states) and the
  state goes CLOSED, so every state-gated hook (accounting, delivery, TX fence, cleanup gate)
  turns inert. The latch is honoured by the parent's existing fences — V21 verified that
  cleanup, add-peer, set_key, join_work, scan, config and retire already check
  `first_error`/`closing`, and an HIF local failure aborts normal state and blocks every send
  entrypoint with no MAC pointer — so no redundant per-callsite guard or framework is added.
- **RX FIFO vs TC4 credit**: the RX FIFO is retired by `receive_packet`'s complete read /
  post-WRPLR, separate from the TC4 page credit that reconciles the enable/disable command; the
  central accounting reads an already-retired frame, and the state machine reconciles only the
  command's page credit.
- **Cleanup gate**: the inherited healthy cleanup may submit only once the diagnostic owns no
  un-retired command (`mt6797_native_diag_cleanup_allowed`: never armed, or fully closed) — the
  disable is retired before cleanup. Any ambiguity leaves only the one-shot reviewed recovery;
  no retry.

## Observation, positive/negative, and the honest limit

Observation is a fresh post-switch, boot-bound Wi-Fi SSH challenge (the existing
`laptop-wifi-ssh`, reused one-shot — not modified), with ordinary RX delivered exclusively as
protected-native: a completed exchange proves mac80211 decrypted, MIC-verified and
replay-accepted the native MPDUs under the live key — no ad-hoc verifier, no key export, no
bespoke crypto. **Positive**: at least one native frame authenticated by mac80211 and the
challenge completes (route-4 precondition met for that sample — not sustained operation, not
the enforcement answer, not completion). **Negative / coexistence failure**: association drops,
no native frame, or the challenge does not complete → **inconclusive**, stop + one-shot
recovery. Normal valid traffic traversing the path shows the path works; it does **not** by
itself prove hostile-replay rejection, and one negative does not close all raw modes.

## Tests (focused, offline; run against the applied tree)

- `tests/run-native-diag-test.py` → `native-diag-test.c` (ASan/UBSan): the ceilings, the
  no-crypto-bypass / ALLOW_SAME_PN-clear flag proof, the budget step, the 16-byte SET_MONITOR encoder, and the **worker-state/ledger
  transitions** (IDLE→ENABLE_PENDING→ACTIVE→DISABLE_PENDING→CLOSED, the deadline/poison
  no-radio latch, the cleanup-allowed gate and the prospective admit).
- `tests/run-native-rx-test.py` → `native-rx-test.c` (ASan/UBSan): the strict decoder across
  **all 16 group masks × pad × QoS** accepted at the source offsets with verbatim length, and
  every withheld shape (HDR_TRAN, AMSDU, unprotected, MoreFragments, Order, fragment,
  ToDS/non-data, non-peer, CCMP-shape, bad-FCS, length mismatch, short, wrong channel).
- `tests/run-native-loop-test.py` → `native-loop-test.c` (ASan/UBSan): an
  **event-sequence model of the worker control loop** following the whole phase
  contract. It proves: the step/queue order (step → the parent's lower-deadline
  `end_data` → TX queue selection) so the disable/page fence is set in the **same
  iteration** before the reserved deauthentication can be selected; the window
  ends on a **sample ceiling OR any data-phase end** (lower deadline, **PID
  budget** determined in the queue path, association loss), driving the step to
  disable and the TX fence to hold; a **prospective sample bound** (reserving a
  full HIF-max read, not post-read length) so no read crosses a ceiling; a
  **finite owed-completion drain** (≤ 64 reads / 256 KiB / 750 ms, below the
  parent deadlines, checked even on an empty stream) that fails through the
  normal terminal if an owed exact TX-done cannot retire; **post-stop only the
  exact TX-done (ID 0x0f) retires** — the broad control dispatcher and all other
  classes are gated; **DISABLE_PENDING reads no generic RX** (the disable credit
  retires by the register guard); and the sticky plaintext withhold never
  reopens legacy RX through CLOSED.

The concurrency, credit, expiry and recovery wiring in `mac.c` is not host-compilable; the loop
model mirrors its control order and must be kept in sync with the worker, its real compile is the
managed Buildbox build after review, and its behaviour is the runtime's. No
build, device, radio or crypto step is part of authoring 0181.
