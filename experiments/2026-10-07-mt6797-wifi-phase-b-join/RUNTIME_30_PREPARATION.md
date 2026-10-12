# Runtime 30 preparation: the runtime 29 protocol on candidate 29 (proposal 0177)

Status: candidate 29 composed and validated by the custodian at 6e6f26b2 from the
compile-34 package `f6ef3ead…` (built input 4cf4b465, proposals 0163 to 0177) with
candidate 28's RAM root, board DT and kernel config byte-identical (`449832a3…`,
`25ab60f4…`, `975f8703…`; helper, supplicant, PSCI and `clk_ignore_unused`
preserved); boot image `65191c11…` (12300288 bytes), full padded boot2 `27005b8f…`
(exact 16 MiB). [results/candidate-29.json](results/candidate-29.json) (SHA-256
`aa27b4cf…`) is the receipt's exact bytes and `runtime-30/results/candidate.json` its
copy. The current boot2 content is the installed candidate 28 (`92bf31d0…`); the stock
boot verified live by the custodian after runtime 29 is `d1c8e5cc…` (reverified at
deployment). The custodian rederives the live GPT and verifies the predecessor with the
reviewed guard at deployment; the generated installer, the device guard, the full
readback, the clean shutdown, the identity checks, the native recovery and the full-log
seal are unchanged except for these identity bindings. The custodian remains the sole
device custodian; the owner selects boot2 physically. No device step has run.

## What differs from runtime 29

Kernel, proposal 0177 only (reviewed by source digest: `mac.c` `9ff0ad54…`,
`group-data.h` `7c0d05ea…`, `action-frame.h` unchanged `51a19415…`): the target's
group data in the descriptor variant runtime 29 refused at cleanup stage 0 (type 2, no
status groups, WLAN index 255, byte 9 zero, status exactly 0xc200, the keyed class's
frame conditions) is discarded, never delivered or interpreted, while the cleanup is
requested and not done and the group key removal command has been submitted (the state
the worker sets at that submission; the discard does not wait for the command's
credit). The first eight are recorded, the total before the stage-3 record; the
lifetime's packet budget and the cleanup's own deadline bound it. Before that
submission, or after stage 3, the variant is a refusal as before. The keyed decoder of
0164 is unchanged; no other shape is admitted.

Nothing else: the wrapper, `join-once.sh`, the laptop helper, the credential and
address handling, the ping and SSH budgets, the native recovery, the decoders' gates
and every radio, TX and time budget are [RUNTIME_29_PREPARATION](RUNTIME_29_PREPARATION.md)'s,
with runtime 30, capture 30, session 30 and deployment 29 in their place. The classifier
reads the cleanup discard records and their total (bound to the one group key removal
record's window and to the first min(total, 8) records). One test only, with the
reviewed native recovery once after the evidence is sealed.

## Hypothesis, unique measurements and branches

Hypothesis (a next-runtime hypothesis; runtime 29's refused packet is read as
consistent with the after-removal window, not as proof of hardware key retirement): the
AP's group frames arriving during the cleanup are discarded and counted, the cleanup
stages 1 to 3 are recorded and the lifetime ends without a footer; the beacon total
with its keyed part and the cleanup discard total are recorded at stage 3; the lease,
the ping replies and the laptop's Wi-Fi SSH exchange are observed again and reported
apart; none is implied by another.

Unique measurements: the `cleanup group frame discarded` records (first eight,
numbered) and `cleanup group frames discarded: total`; the `beacon delivered` records
and `beacons delivered: total ... keyed`; the data phase's end record and reason; the
completions by PID; the deauthentication's completion, the key removal commands and
their credits, the cleanup submissions 0 to 2 and the stage-3 record; any footer's
status and branch; the session's `udhcpc`, `ping` and the laptop's Wi-Fi SSH receipt
bound to `mainline_boot`, each reported as what it is.

Branches, each ending the lifetime exactly once:

1. Stages 1 to 3 recorded without a footer: 0177 observed if any cleanup discard was
   recorded (unobserved if none arrived), the first healthy C3 lifetime of the series;
   the network terms decide the next direction individually.
2. A refusal of another shape during the cleanup: recorded by its descriptor and header
   fields, fail-stop, seal, reviewed native recovery once; the next decision is taken
   from those fields, not by broadening on the device.
3. A disconnect, or a branch-9 footer: read from the supplicant fields and the
   delivered-beacon records, as runtime 28's branches state.
4. Any other named refusal or fault (a frame-gate refusal elsewhere, a key refusal, a
   data TX timeout, the grant too close to its end, the packet budget): fail-stop as
   before, seal, reviewed native recovery once.

No branch repeats a boot without a decision-changing change. Nothing is reconnected or
rekeyed. No Wi-Fi operational, reliability or replay-protection claim follows from any
branch; `wifi_operational` stays false.

## Bindings

| Adapter | Runtime 30 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 4cf4b465…`, `PACKAGE f6ef3ead…` (6e6f26b2); every other pin unchanged |
| `install-passive.py` | predecessor `92bf31d0…` (installed candidate 28), receipt `mt6797-wifi-phase-b-deployment-29`, `results/candidate-29.json`, slot `aa27b4cf…` |
| `capture-private.py` | `capture-30`, `session-30/deployment-summary.txt`, `results/candidate-29.json`, slot `aa27b4cf…` |
| `passive-session.py` | `results/candidate-29.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-30`, `capture-30`; identity `runtime-30/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-29.json` against the compile-34 input and package, both slots, predecessor `92bf31d0…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-30` only |
| `join-once.sh`, `laptop-wifi-ssh.py` | unchanged from runtime 29 |

## Evidence and claims

As in runtimes 21 to 29: the sealed kernel log classified by `classify-join.py`, the
session's fixed fields and phrase counts, the private supplicant log digested (the
disconnect fields extracted locally if any), the laptop's Wi-Fi SSH receipt bound to
`mainline_boot`. Runtime 29's original evidence and verdicts stay intact.
