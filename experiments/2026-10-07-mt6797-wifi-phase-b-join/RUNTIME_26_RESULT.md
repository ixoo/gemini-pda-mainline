# Runtime 26 result: negative, the target's beacon in a keyed descriptor variant refused before any data frame

Boot: mainline `841a37db-b274-4f7f-9947-420673ecc3f3` on candidate 25 (compile 30,
package `2b219cf3…`, input da50d8b6, boot2 `b38d25a9…`), session tools at 82d18725,
launched once by the custodian after deployment 25 (predecessor candidate 24
`35014d84…`, stock boot `c49e4d59…`). Evidence: the custodian's eleven sanitized
uploads (join diagnostic records, log, supplicant-log, session, native-request and
Wi-Fi SSH results, body fields, Phase A result); kernel log sealed complete (156395
bytes, 2038 records, SHA-256 `bc03df07…`); supplicant log complete (26527 bytes,
SHA-256 `c60c4420…`). No raw capture, address, body or credential is published.

## Observed

- Initialization passed; the association exchange completed and the supplicant
  reported handshake completion (its own state, not firmware key proof).
- 0169 observed (one group-data discard with WLAN index 2), 0168 observed (one
  broadcast Action discard), the runtime 18 class discarded once; the pairwise and
  group commands submitted and credited (0170), both add-key-done windows recorded
  (attribution by window only).
- 0172 observed up to its opening: `data phase: budget_ms=6172 teardown_margin_ms=5000
  inside_grant=1` with no channel abort before it.
- Before any data frame, at 192072472 µs, one packet refused at the frame gate: 442
  bytes in all (378 wire bytes at offset 64, groups 1 to 3), type word 0xee01,
  descriptor bytes 08 28 18 04 02 40 04 e0 (broadcast match flag only, channel 40,
  native untranslated 24-byte header, BSSID field 1, WLAN index 2, TID 0, security
  mode 4, status 0xe004), the summary's first frame-control byte 0x80 (management
  type, Beacon subtype; the flag byte is not in the summary), receiver not this
  station, transmitter the target (the summary's explicit comparisons). The receiver
  address, BSSID, flag byte, sequence and body were not retained. Fail-stop at
  192075072 µs: status -71, branch 7, TC4 debt 0. The data phase ended on the
  supplicant's disconnect (elapsed 1384 ms) with every data counter 0 and
  `tx_credits` 0. No data frame was submitted, so 0172's TX and credit hypothesis is
  unmeasured, not refuted.
- Host: the join phase completed framed and terminal; `udhcpc` ran (exit 1, no
  lease); no ping, listener or Wi-Fi SSH exchange; the original session result's
  C3 Wi-Fi SSH term is null because the host session completed before the 90 s
  helper, and stays as recorded; the separate final helper receipt saw no readiness
  marker (92 s), attempted nothing, bound to boot 841a37db. Verdicts: bounded join,
  handshake and data false; C2 false; C3 false; not malformed; refusal and terminal
  failure recorded; `data_phase_opened` and `data_phase_inside_grant` true,
  `data_phase_budget_ms` 6172. These stand as computed.

## Diagnosis (source, not hardware proof)

The join worker skips, without a record, every beacon or probe response the scan
decoder parses; that decoder requires security mode 0 and a clean status word. The
observed descriptor carries WLAN index 2 (the broadcast entry the station record
declares and the group key was installed under), security mode 4 (that entry's
cipher context in the pinned layout) and status 0xe004 (bit 2 is
`RX_STATUS_FLAG_CIPHER_MISMATCH`, an unprotected frame against a keyed entry; the
ICV-error flag is clear), so it fails exactly the decoder's two conditions and reaches
the gate. Whether beacons arrived in earlier runs, or how often, is unobserved; this
variant can appear only after the group key exists, which runtimes 20 to 24 never
reached and runtime 25 held for about 950 ms after its channel abort. In the pinned
vendor driver a received beacon goes to the scan handler; its management path drops
only ICV errors, and only under the MFP build option. The channel order and the
first-data-frame questions of runtime 25 remain open.

## Recovery

One native recovery was requested after the evidence was sealed and confirmed with
the regression check true; a changed-identity stock boot
`010ae842-8c8c-44b0-abe7-9592d99fdb89` was independently verified live. One request
only. The installed boot2 remains candidate 25 (`b38d25a9…`).

## Decision

Proposal 0173 names a narrow class for the worker's existing beacon skip: the
observed conditions (type word 0xee01, match 0x08, descriptor bytes 18 04 02 40 04 e0
with the declared broadcast entry, first frame-control byte 0x80, transmitter the
target) and source-defined conditions the diagnostic did not carry (frame control
exactly 0x0080, broadcast receiver, BSSID the target, fragment 0, the 12 fixed body
bytes present). It is skipped like the clear beacons, counted (first four recorded,
total before the stage-3 record), bounded by the lifetime's packet budget, never
delivered; no discard budget changes. It is a next-runtime hypothesis: a frame that
differs in a source-defined field will be refused as before, and nothing is claimed
about runtime 26 being resolved until measured. One bounded next test: the runtime
26 protocol on a candidate carrying 0173, with 0172's first-data-frame measurements
unchanged. No repeat of candidate 25; no replay-protection or operational claim.
