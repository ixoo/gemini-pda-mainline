# Runtime 29 preparation: the runtime 28 protocol on candidate 28 (proposals 0175 and 0176)

Status: candidate 28 composed and validated by the custodian at 68177109 from the
compile-33 package `bf244275…` (built input 94e9c890, proposals 0163 to 0176) with
candidate 27's RAM root, board DT and kernel config byte-identical (`449832a3…`,
`25ab60f4…`, `975f8703…`; helper, supplicant, PSCI and `clk_ignore_unused`
preserved); boot image `4a7e826f…` (12302336 bytes), full padded boot2 `92bf31d0…`
(exact 16 MiB). [results/candidate-28.json](results/candidate-28.json) (SHA-256
`c3af0e07…`) is the receipt's exact bytes and `runtime-29/results/candidate.json` its
copy. The current boot2 content is the installed candidate 27 (`c45503fa…`); the stock
boot verified live by the custodian is `8e3984fd…` (reverified at deployment). The
custodian rederives the live GPT and verifies the predecessor with the reviewed guard
at deployment; the generated installer, the device guard, the full readback, the clean
shutdown, the identity checks, the native recovery and the full-log seal are unchanged
except for these identity bindings. The custodian remains the sole device custodian;
the owner selects boot2 physically. No device step has run.

## What differs from runtime 28

Kernel, two proposals reviewed by source digest (`mac.c` `5d136f4f…`,
`action-frame.h` `51a19415…`):

- 0175: a regulatory update while the lifetime runs ends it through the one terminal
  path (footer, branch 9, status -ECANCELED) instead of retiring it silently; an
  already-ended lifetime is retired as before.
- 0176: the target's beacons are delivered to mac80211 after an accepted association,
  the clear class the scan decoder accepts and the keyed variant the 0173 decoder
  accepts, exactly as decoded today (the keyed decoder gains an RCPI output, no
  acceptance change), handed over as the passive scan hands beacons over; the first
  four deliveries recorded, the total with its keyed part before the stage-3 record;
  bounded by the lifetime's 32768-packet budget. The connection-monitor flag is not
  declared.

Nothing else: the wrapper, `join-once.sh`, the laptop helper, the credential and
address handling, the ping and SSH budgets, the native recovery, the decoders' gates
and every radio, TX and time budget are [RUNTIME_28_PREPARATION](RUNTIME_28_PREPARATION.md)'s,
with runtime 29, capture 29, session 29 and deployment 28 in their place. The classifier
reads the footer's branch and the delivered-beacon records (first records apart from an
unknown total). One test only, with the reviewed native recovery once after the
evidence is sealed.

## Hypothesis, unique measurements and branches

Hypothesis (a next-runtime hypothesis; runtime 28's end remains a source-supported
inference): the delivered beacons keep mac80211's beacon and connection monitors
satisfied, no nullfunc poll occurs and no local disconnect follows, so the data phase
runs to its budget inside the grant and the driver's own cleanup follows: the reserved
deauthentication completed, both keys removed, the three recorded cleanup stages 1 to
3, no footer. The lease, the ping replies and the laptop's Wi-Fi SSH exchange are
observed again and reported apart; none is implied by another.

Unique measurements: the `beacon delivered` records (first four, numbered) and the
stage-3 total with its keyed part; the data phase's end record and reason; the data
completions by PID with status 0, non-zero and late apart, and the credit chronology;
the deauthentication's completion, the key removals and the cleanup stages; any
footer's status and branch; the session's `udhcpc`, `ping` and the laptop's Wi-Fi SSH
receipt bound to `mainline_boot`, each reported as what it is.

Branches, each ending the lifetime exactly once:

1. The data phase ends by its budget and the cleanup stages 1 to 3 are recorded without
   a footer: 0176 observed, the first healthy C3 lifetime; the network terms decide the
   next direction individually (a lease without ping replies, or replies without the
   SSH exchange, are separate negative results, not a fault of 0176).
2. A disconnect again, followed by a branch-9 footer: the regulatory notifier's
   involvement in this boot is observed (0175 observed); the disconnect's cause is
   re-read from the supplicant fields and the delivered-beacon records (whether beacons
   were delivered before it), and decides the next proposal.
3. A disconnect again without any footer: this boot's stop is unresolved; the other
   close paths (interface removal, stop, scan cancellation, the prepare-tx refusal)
   are the next audit. This does not refute runtime 28's inference, which stays an
   inference.
4. Any other named refusal or fault (a frame-gate refusal, a key refusal, a data TX
   timeout, the grant too close to its end, the packet budget): fail-stop as before,
   seal, reviewed native recovery once.

No branch repeats a boot without a decision-changing change. Nothing is reconnected or
rekeyed. No Wi-Fi operational, reliability or replay-protection claim follows from any
branch; `wifi_operational` stays false.

## Bindings

| Adapter | Runtime 29 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 94e9c890…`, `PACKAGE bf244275…` (68177109); every other pin unchanged |
| `install-passive.py` | predecessor `c45503fa…` (installed candidate 27), receipt `mt6797-wifi-phase-b-deployment-28`, `results/candidate-28.json`, slot `c3af0e07…` |
| `capture-private.py` | `capture-29`, `session-29/deployment-summary.txt`, `results/candidate-28.json`, slot `c3af0e07…` |
| `passive-session.py` | `results/candidate-28.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-29`, `capture-29`; identity `runtime-29/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-28.json` against the compile-33 input and package, both slots, predecessor `c45503fa…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-29` only |
| `join-once.sh`, `laptop-wifi-ssh.py` | unchanged from runtime 28 |

## Evidence and claims

As in runtimes 21 to 28: the sealed kernel log classified by `classify-join.py`, the
session's fixed fields and phrase counts, the private supplicant log digested (the
disconnect fields extracted locally if any), the laptop's Wi-Fi SSH receipt bound to
`mainline_boot`. Runtime 28's original evidence and verdicts stay intact.
