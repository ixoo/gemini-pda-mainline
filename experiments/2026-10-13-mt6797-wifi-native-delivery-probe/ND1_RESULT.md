# ND1 result — native-crypto-delivery diagnostic (negative; host defect, not a firmware verdict)

One reviewed run; recovery NOT yet confirmed (see below). This records the outcome
truthfully: the native diagnostic did not run because of a HOST-side command
validation defect, so it is NOT a firmware-capability result. Sanitized IDs only.

## Identity

- Candidate ND1: the exact committed receipt is
  `results/native-delivery-candidate.json`
  (kernel_build_commit `d104654db3f9c236b9595fd402e789c313fda2c6`,
  kernel_package_sha256 `aa305e666006ab8a4c70d881a1f14ce8b64991a5431ff733c2831f042d08cfec`,
  release `7.1.3-gemini-a53-wifi-native-delivery-diag`, physical_admission false,
  native_delivery_diag true, boot2-padded.img sha256
  `76a9d71925d9045f…`), patch 0181 on the C32 parent; the candidate receipt sha256
  is `e1c4e2d3eea71f808ee1d9d7f860c1fe43014d4eed00361dfd6562e480ee0c06`. Installed
  under the reviewed boot2 guard (predecessor C33 full-partition
  `74c5f71175a157c4ed202780382f04e9baf600ddcacf8f7751c1096ae9c85c29`).
- Tooling pin `2e347e62`; mainline boot `90f6c5ae-cdf5-4c8a-9e9e-bc0a3b25a61a`.

## What happened

Phase-A capture PASS (`ready_for_scan=true`). The station associated and reached a
keyed data phase (budget_ms 6184, teardown margin 5000, inside grant 1). The native
diagnostic then attempted its single SET_MONITOR enable and was refused LOCALLY:

    one-shot WLAN native-diag: state=4 act=1 total=0 native=0 bytes=0
    one-shot WLAN join stopped: status=-125 first=-22 submitted=0x801 debt=0 cleanup=0 branch=8

`first=-22` (EINVAL) is a host refusal (`first_error`), not a firmware response;
`status=-125` is the resulting ECANCELED lifetime end. The native-diag advanced only
IDLE→ENABLE_PENDING and then CLOSED (state=4, act=1=SUBMIT_ENABLE) with nothing
delivered: total=0, native=0, bytes=0. No post-ACTIVE Wi-Fi challenge was made.

## Verdict (NOT a PASS)

Final session exit 1: `native_delivery_pass=false`, eligible=false,
authenticated=false, native=0, observed sequence `[[4,1]]`, fault=true. The
classifier correctly rejected it (the owned sequence `[(1,1),(2,0),(3,2),(4,0)]`
was never produced; fault present). Evidence integrity held: all 63 pre-recovery
seal hashes matched, `preservation.log_complete=true`.

## Host defect vs firmware capability (kept separate)

The cause is a HOST defect: proposal 0181 added the HIF native wrapper
(`mt6797_hif_native_monitor` → `mt6797_hif_send_join_command`, CID 0xFC) but did
NOT add a 0xFC case to the command validator `mt6797_join_prepare_command`
(join-command-submit.h), whose `switch (cid)` admits only 0x07/0x0a/0x12/0x13/
0x14/0x1c and returns -EINVAL by default. So the SET_MONITOR command was rejected
before any PIO submission. The firmware's native-crypto-delivery behaviour is
therefore UNOBSERVED — the command never reached it; no firmware acceptance,
rejection or mode semantics can be inferred from this run. (Independent review and
an OpenCode memo reach the same conclusion; TC4 credit return would prove only
transport-ledger retirement, never firmware acceptance, and no monitor
join-submitted bit exists in 0181.)

## Recovery — INCOMPLETE (not confirmed)

One recovery request was made; the return collector made 12 attempts over ~165 s
and the return is UNCONFIRMED. `regression_pass=false` AND `recovery_confirmed=false`;
the observation baseline-only check passed, so no physical regression failure is
inferred without individual results. The known-good Gemian LAN read-only probe was
unavailable. The owner state question is pending; no repeated recovery was attempted.
This record will be finalized when recovery is confirmed.

## Fix (authored for review; no build yet)

Add a diagnostic-config-gated `case 0xfc` to `mt6797_join_prepare_command` that
admits exactly 16 bytes with the exercised fields validated (ucEnable 0/1,
ucPriChannel 40, band/SCO/width/S1/S2 and the 9 reserved bytes zero), under
`#ifdef CONFIG_MT6797_NATIVE_DELIVERY_DIAG` so a normal build still refuses 0xFC.
A validator-path test (not the prior encoder-only test) must exercise
`mt6797_join_prepare_command` with CID 0xFC. Root reviews the code before any build.
