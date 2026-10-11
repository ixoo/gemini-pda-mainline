# Runtime 25 result: negative, the first data frame produced no TX status after the channel release

Boot: mainline `001b1593-69d6-46fc-8687-5c58f31acf45` on candidate 24 (compile 29,
package `0ce04178…`, input 1057b6b5, boot2 `35014d84…`), session tools at 84151133,
launched by the custodian after deployment 24 (predecessor candidate 23 `1b07a2bb…`,
stock boot `40295547…`). Evidence: the custodian's sanitized uploads (join
diagnostic records, log, supplicant-log, session, native-request and Wi-Fi SSH
results, body fields); kernel log sealed complete (155392 bytes, 2035 records,
SHA-256 `52b6dbfb…`); supplicant log complete (26696 bytes, SHA-256 `8230cab9…`).
No raw log, address, body or identifier is published.

## Observed

- The association exchange completed; the supplicant reported handshake completion
  (its own state). 0171 observed: one directed Action discard with security mode 4
  and status 0xe004 after the pairwise credit. No broadcast Action and no group-data
  frame this boot (0168 and 0169 unobserved).
- 0170 observed again: pairwise command (sequence 25), its credit, message 4 in
  flight, the first add-key-done, `key credit returned: pairwise`, message 4's TX
  done. Then the group command (sequence 26), its credit, the second add-key-done,
  `key credit returned: group`; the CH_PRIVILEGE abort's credit and `channel
  released: sequence=27`; `data phase: budget_ms=60000 teardown_margin_ms=5000`.
  Kernel timestamps: group submit 81242795, its credit 81266628, second key-done
  81267695, group credit returned 81269025, release credit 81290630, channel
  released 81291713, data phase 81292780 (microseconds).
- `data TX: first pid=5 pages=3 bytes=342` at 81454660; then no TX-done record
  and no delivered data RX; the lifetime stopped (-110, branch 1, first 0, TC4 debt 0,
  cleanup 0) at 82222607, 767947 µs after the data TX, at the frame deadline; the
  supplicant's disconnect then ended the data phase (`reason=disconnect`,
  elapsed 2118 ms, rx 0, tx_queued 1, tx_done 0, tx_failed 0). The TC1 page return
  is not recorded by this driver, so whether the frame's pages returned is
  unobserved. The device's `udhcpc` ran (exit 1, no lease); no ping, listener or
  Wi-Fi SSH exchange; the laptop helper saw no readiness marker (92 s).
- Host verdicts as computed: C2 false, C3 false, `malformed_stage_record` true,
  `terminal_failure_recorded` true, `refusal_recorded` false, both key commands
  submitted and credited. These stand as recorded. Separately attributed: the
  malformed flag came from the classifier's lifetime rule requiring a stage-1
  release record for every release record; a fail-stop after the release reaches
  no cleanup, so the rule, not the records, produced it. The rule is corrected in
  this commit; the original verdict is not rewritten.
- Not firmware evidence: the supplicant's CONNECTED, PTK and GTK lines are its
  state, not key installation; the credits are attributed by order; the
  add-key-done events by window only.

## Diagnosis (source and reference, not hardware proof)

- The vendor writes every TX frame through the same HIF port; our TC1 and TC4
  frames use that port. The pinned TXD layout confirms our TC1 descriptor (LMAC
  queue 1, non-802.11 long format, Ethernet II, protected, TID 0) equals the
  vendor's data descriptors in the run 3 ledger and differs from our working
  management and security descriptors only by port/queue and the protected bit.
  The vendor's TC1 data frames received the same TX-done event our decoder admits;
  that says nothing about our runtime's routing of such an event: none was recorded
  or routed here, and whether one arrived at the HIF is unobserved.
- Commands: this driver sends SET_RX_FILTER, SET_BSS_INFO (connection state
  connected, at activation after the association, with its credit awaited before
  the BSS counts as configured), UPDATE_STA_RECORD, the key commands, station
  removal and CH_PRIVILEGE. Of the vendor's post-association set in the run 3 ledger
  it does not send INDICATE_PM_BSS_CONNECTED, SET_BSS_RLM_PARAM, UPDATE_WMM_PARMS,
  ROAMING_TRANSIT or MAC_MCAST_ADDR. In that ledger every one of the vendor's first
  data frames went out inside its channel grant (request at 108.572 s, first data
  108.63 to 109.6 s, abort at 112.570 s) and data continued after the abort.
  Proposal 0165 aborted the privilege before the first data frame: an order the
  vendor never showed.
- Inference, not measured: with the privilege aborted and without the vendor's
  remaining post-association commands, the LMAC data queue may have had no channel
  to serve, so the frame neither completed nor was reported. Running the data phase
  inside the grant is an ordering diagnostic, not a proven cause.

## Recovery

One native recovery was requested after the evidence was sealed; the collector
confirmed a changed-identity stock boot `c49e4d59-0795-488e-bf33-68507f2a4549` on
its second attempt after 15.4 s, with the regression check true. One request only.
The installed boot2 remains candidate 24 (`35014d84…`).

## Decision

Proposal 0172: the data phase opens inside the live grant after the group key's
credit (no abort; cleanup stage 1 returns the privilege as before 0165); its
deadline is the budget or the grant's end minus a 2500 ms tail, whichever is
sooner (the tail covers the last admitted frame's 750 ms completion, then the
dequeue of the deauthentication reserved at association, which needs 850 ms of
grant room covering its own completion, then the four cleanup commands and the
poll and HIF latencies: 750 + 850 + 400 + 120 = 2120 ms); the deauthentication
does not wait for TC1 pages, the cleanup commands do, bounded by the lifetime
deadline; TC1 credit returns are recorded and a data frame still
in flight at its deadline is named with the TC1 ledger's state. If the first data
frame then completes, the next question is which of the vendor's remaining
post-association commands allows data after the release; if it does not, the TC1
records decide between a consumed frame and a stalled one. No budget is raised; no replay-protection or operational
claim. Compile 30 follows the custodian's review; no repeat of candidate 24.
