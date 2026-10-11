# Runtime 21 result: negative, fail-stop at the frame gate before the key commands

Boot: mainline `41fe011b-49f7-4292-a598-5f07c8dc34af` on candidate 20 (compile 25,
package `cca46f58…`, boot2 `d01f3304…`), session tools at 0748173a, launched by the
custodian after deployment 20 (predecessor `8d3289a1…`, stock boot `f73e5f74…`).
Evidence: the custodian's sanitized uploads (join diagnostic records, supplicant
fields, supplicant-log and log results, the Phase A result, the session result,
the Wi-Fi SSH receipt); kernel log sealed complete through the seal (154538 bytes,
2029 records, SHA-256 `2394077e…`); supplicant log complete (24060 bytes, SHA-256
`71d23550…`). No raw log, address, body or identifier is published.

## Observed

- Phase A: common init 285/285, calibration task 4, ready for scan; Phase B scan
  ran once.
- Join: authentication and association (status 0) exchanged and acknowledged;
  station activated; message 1 delivered (translated, pre-activation tag 15),
  messages 2 and 4 sent and acknowledged, message 3 delivered (tag 1). The
  supplicant logged the four handshake messages, PTK and GTK installation, key
  negotiation completed and one CTRL-EVENT-CONNECTED, then one
  CTRL-EVENT-DISCONNECTED.
- After message 4: one directed clear Action frame from the target discarded (the
  runtime 18 class, count 1); then one packet refused at the frame gate: 708 bytes
  in all, type word 0xee01, descriptor bytes 08 28 18 3c ff 00 00 e0, groups 1 to
  3, header at 64, no translation, first payload byte 0xd0. Fail-stop: stopped
  with status -71, branch 7, nothing submitted after.
- The supplicant's pairwise and group key commands then arrived and were refused
  (-71 and -95) because the lifetime had stopped. No key command, channel
  release, data phase, DHCP, ping or listener ran; the laptop's Wi-Fi SSH check
  saw no readiness marker within its budget (92 s) and attempted nothing.
- Verdicts: C2 false, C3 false. The classifier at 0748173a reported the run as
  malformed because its EAPOL and discard window required a deauthentication TX
  that a fail-stop never sends; that is a classifier placement rule corrected
  after this run (the records are placed and the refusal decides), not a record
  defect. Reclassified, the run is a recorded refusal with a terminal failure.

## Not observed and not claimed

The frame's transmitter, BSSID, category and body were not retained; its sender
is unknown. No network function, no key installation in firmware, no data path.
The fail-stop was triggered by the driver's own receive-frame gate; no firmware
fault was reported, and the firmware's execution after the stop was not
independently measured. The fail-stop records are complete.

## Recovery

The reviewed recovery was requested after sealing. The native return collector's
budget (12 slots, 180 s) was consumed with `recovery_confirmed` false and
`regression_pass` false, and one subsequent bounded known-good LAN identity check
timed out; those receipts are preserved as recorded. Separately and later, after
the owner reconnected the device to Wi-Fi from its UI, one read-only identity
check confirmed stock Gemian 3.18.41+ on boot `a2265c06-5946-4ffe-a7bb-5769887ef8d1`
(a boot distinct from the mainline boot and from the pre-deployment stock boot);
the custodian uploaded that stdout (SHA-256 `0a44e7b8…`). The late confirmation
does not change the original timeout receipts. The installed boot2 remains
candidate 20 (`d01f3304…`). The one reviewed native restart was requested and
occurred; no additional reboot, recovery retry or alternate recovery path was
performed.

## Decision

Proposal 0168 names the refused class by its observed descriptor fields and the
source-defined frame conditions, and discards it undelivered at any stage, at
most eight per lifetime, the ninth refused. The classifier closes the
fail-stopped window at the stopped footer and places the new record up to the
stage-3 terminal. Compile 26 follows from the pushed inputs; a candidate and one
boot follow the custodian's review. No repeat of candidate 20.
