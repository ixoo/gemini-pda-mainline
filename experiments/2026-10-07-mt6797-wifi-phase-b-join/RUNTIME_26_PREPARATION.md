# Runtime 26 preparation: the data phase inside the channel grant on candidate 25 (proposal 0172)

Status: candidate 25 composed and validated by the custodian at 04894e89 from the
compile-30 package `2b219cf3…` (input da50d8b6, proposals 0163 to 0172) with
candidate 24's RAM root byte-identical (`449832a3…`), the same board DT
`25ab60f4…` and kernel config `975f8703…` (all three byte-compared by the custodian;
PSCI and `clk_ignore_unused` preserved; helper and supplicant unchanged); kernel
image `e6dbc40a…` (decompressed one 64 KiB step larger than compiles 19 to 29 with
the configuration unchanged), boot image `195c7683…` (12300288 bytes), full padded
boot2 `b38d25a9…`. [results/candidate-25.json](results/candidate-25.json) (SHA-256
`19a7a340…`) is the receipt's exact bytes and `runtime-26/results/candidate.json`
its copy. The current boot2 content is the installed candidate 24 (`35014d84…`); the
stock boot reverified by the custodian is `c49e4d59…`. The custodian rederives the
live GPT and verifies the predecessor with the reviewed guard at deployment; the
generated installer, the device guard, the native recovery and the full-log seal are
unchanged except for these identity bindings. The custodian remains the sole device
custodian. No device step has run.

## What differs from runtime 25

Kernel, proposal 0172 only: the data phase opens inside the live channel grant after
the group key's credit (no CH_PRIVILEGE abort before data; cleanup stage 1 returns
the privilege as before 0165); its deadline is the 60 s budget or the grant's end
minus a 2500 ms tail, whichever is sooner (about five seconds of data on this
protocol's 9 s grant); outstanding TC1 pages hold only the next data frame, the
reserved deauthentication does not wait for them, the cleanup commands do within
the lifetime deadline; TC1 credit returns are recorded (the first eight, the total in
the end record) and a data frame still in flight at its deadline is named with the
TC1 ledger's state. No budget is raised; no admission, key, class or radio behaviour
changes; the host wrapper (with its keepalive line), the laptop helper and every bound
are runtime 25's. The 0168 to 0171 hypotheses and branches stand by reference. One
test only, with the reviewed native recovery once after the evidence is sealed.

## Hypothesis, unique measurements and branches for 0172

Hypothesis (an ordering diagnostic, not a proven cause): with the channel privilege
retained through the data phase, the first data frame on TC1 completes (a TX-done
record for its PID) and its pages return (a `data credit` record), where runtime 25,
after the abort, recorded neither.

Unique measurements, all sanitized driver records: `data phase: budget_ms=<n>
teardown_margin_ms=5000 inside_grant=1`; `data TX: first pid=<p> pages=<n>
bytes=<b>`; the `TX done: pid=<p> status=<s>` record for that PID, reported with
its status (0 and non-zero separately: the completion event is not an
acknowledgement or a delivery); `data credit: pages=<n> debt=<d> count=<c>` records
in chronology with the frames; `data TX timeout: pid=<p> debt=<d> credits=<c>
elapsed_ms=<e>` if a frame did not complete; the `data phase end` record with
`tx_done`, `tx_failed`, `rx_unicast` and `tx_credits`; the three cleanup stages
inside the grant. Page consumption (credits), TX completion (TX done) and delivery
(RX) are distinct and each is reported on its own; none is a network-function claim
by itself. The `credits` field of the timeout record and `tx_credits` are cumulative
over every TC1 frame of the phase, so a positive total alone does not show that the
timed-out frame's pages returned: that is read from the timeout record's `debt`
(0: the current frame's pages returned; equal to its page count: none; between:
partial) together with the chronology of the `data credit` records against the
frames, and the first PID is kept apart from later ones. A TC1 return after the
phase ended and before the healthy cleanup is an observed delayed return, not a
reconciliation defect. The session's `udhcpc`, `ping` and the laptop's Wi-Fi SSH
receipt remain the only network-function evidence.

Branches, each ending the lifetime exactly once:

1. The first data frame's TX done recorded (its status reported, 0 or not) and its
   pages credited in chronology; the phase runs to its budget (the grant's remainder)
   or ends on the supplicant's disconnect; the cleanup completes inside the grant:
   0172's ordering observed. Whether DHCP, ping and the SSH exchange fit the
   shortened phase is reported from the session fields. The next direction is the
   vendor's remaining post-association commands that allow data after the release and
   the full 60 s phase.
2. TX done recorded for the first frame but no `data credit` record for it before
   the phase ends: completion without an observed page return; reported as such,
   with any return after the phase and before the cleanup reported as a delayed
   return; the next direction is the TC1 reconciliation chronology, not the radio
   path.
3. No TX done; a `data TX timeout` record whose `debt` is 0 for the timed-out frame
   (its pages returned, by the record's debt and the credit chronology, not by the
   cumulative total): the firmware consumed that frame's pages without reporting
   completion; the next question is the descriptor and queue, and an exact firmware
   question may go to the custodian for OpenCode. A partial debt is reported as
   partial.
4. No TX done; a `data TX timeout` record with the frame's full page count still in
   debt: retaining the grant did not resolve the timeout; the frame neither completed
   nor returned its pages inside the grant; other missing conditions may coexist, so
   the next question is the firmware's remaining post-association state (the commands
   this driver does not send), an exact question for OpenCode.
5. The data phase refused to open (grant too close to its end), a ninth discard, a
   neighbouring frame shape, a key refusal or any other named refusal: fail-stop as
   before, seal, reviewed recovery.

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed. No replay-protection or operational claim follows from any
branch.

## Bindings

| Adapter | Runtime 26 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT da50d8b6…`, `PACKAGE 2b219cf3…`; every other pin unchanged |
| `install-passive.py` | predecessor `35014d84…` (installed candidate 24), receipt `mt6797-wifi-phase-b-deployment-25`, `results/candidate-25.json`, slot `19a7a340…` |
| `capture-private.py` | `capture-26`, `session-26/deployment-summary.txt`, `results/candidate-25.json`, slot `19a7a340…` |
| `passive-session.py` | `results/candidate-25.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-26`, `capture-26`; identity `runtime-26/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-25.json` against the compile-30 input and package, both slots, predecessor `35014d84…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-26` only |
| `join-once.sh`, `laptop-wifi-ssh.py` | unchanged from runtime 25 |

## Evidence and claims

As in runtimes 21 to 25: the sealed kernel log classified by `classify-join.py`
(which knows the 0172 data-phase shape and the new records), the session's fixed
fields and phrase counts, the private supplicant log digested, the laptop's Wi-Fi SSH
receipt bound to `mainline_boot`. `wifi_operational` stays false; a lease, ping
replies and the boot-bound SSH exchange are the only network-function evidence and
are reported as such. Runtime 25's original evidence and verdicts stay intact.
