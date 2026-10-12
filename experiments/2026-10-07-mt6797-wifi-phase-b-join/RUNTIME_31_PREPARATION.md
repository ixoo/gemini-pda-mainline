# Runtime 31 preparation: the runtime 30 protocol on candidate 30 (proposal 0178)

Status: candidate 30 composed and validated by the custodian from the compile-35
package `bfa7516a…` (built input 8ccf249c, proposals 0163 to 0178) with candidate 29's
RAM root, board DT and kernel config byte-identical (`449832a3…`, `25ab60f4…`,
`975f8703…`; helper `bc499f28…`, supplicant `0487b710…`, PSCI and `clk_ignore_unused`
preserved); boot image `7aee04b8…` (12302336 bytes), full padded boot2 `e758bf36…`
(exact 16 MiB). [results/candidate-30.json](results/candidate-30.json) (SHA-256
`44117611…`) is the receipt's exact bytes and `runtime-31/results/candidate.json` its
copy. The current boot2 content is the installed candidate 29 (`27005b8f…`); the stock
boot verified live by the custodian after runtime 30 is reverified at deployment. The
custodian rederives the live GPT and verifies the predecessor with the reviewed guard at
deployment; the generated installer, the device guard, the full readback, the clean
shutdown, the identity checks, the native recovery and the full-log seal are unchanged
except for these identity bindings. The custodian remains the sole device custodian; the
owner selects boot2 physically. No device step has run.

## What differs from runtime 30

Kernel, proposal 0178 only, after 0177 in canonical order. Reviewed by source digest:
the built driver files are `mac.c` `e9882ff1…` and `data-rx.h` `fa65a7e4…`
(`group-data.h` `7c0d05ea…`, `action-frame.h` `51a19415…` unchanged). The later commit
96fc35e2 recast 0178's comments and message as unmeasured inference; its two driver
files (`mac.c` `5fce99d6…`, `data-rx.h` `411b33f8…`) differ from the built ones in
comments only — with comments stripped and blank lines removed both pairs hash
identically (`mac.c` `231b9e71…`, `data-rx.h` `56b3cf23…`) — so the compiled code is the
reviewed code.

0178 names the data receive class in its LLC-mismatch group variant with a second
decoder in `data-rx.h` (type 2 with status group 4 present, header translation with the
14-byte header, payload format 0 with BSSID field 1, the declared broadcast entry,
security mode 4, a broadcast or multicast match flag with the key id bits free, the
group-4 frame control `0x6208` of a non-QoS FromDS protected data frame from the target
with fragment 0, a group destination and a non-group source) and status exactly
`0xc200`; the 0166 decoder is unchanged. During the data phase, under the data receive
gate's conditions — the data phase open and not ended, both key-install commands
credited (`join_key_pairwise == 1 && join_key_group == 1`, submitted and credited, not a
measured hardware-install proof), no deauthentication done, cleanup not done — that exact
variant is discarded as the pinned vendor data path drops it (`fgDrop = TRUE` on
`HAL_RX_STATUS_IS_LLC_MIS`), never delivered or interpreted, no submission follows. The
first eight are recorded by their descriptor fields and the translated header's type or
length word; the total is recorded before the stage-3 record; the lifetime's packet
budget and the data phase's budget bound it. The unicast form, any other status and every
other shape stay refusals as before. The keyed decoders of 0164 and 0166 are unchanged;
no other shape is admitted. This is the exact variant that stopped runtime 30 at the
frame gate 5.4 s into the data phase (94-byte descriptor, status `0xc200`, group-4 frame
control `0x6208` from the target).

Nothing else: the wrapper, `join-once.sh`, the laptop helper, the credential and address
handling, the ping and SSH budgets, the native recovery, the decoders' gates and every
radio, TX and time budget are [RUNTIME_30_PREPARATION](RUNTIME_30_PREPARATION.md)'s, with
runtime 31, capture 31, session 31 and deployment 30 in their place. The classifier reads
the data-phase LLC-discard records and their total (bound to the data-phase window and to
the first min(total, 8) records) in addition to the cleanup-discard and beacon records.
One test only, with the reviewed native recovery once after the evidence is sealed.

## Hypothesis, unique measurements and branches

Hypothesis (a next-runtime hypothesis; runtime 30's refused packet is read as consistent
with a group frame of the delivered class flagged LLC mismatch, not as proof that the
environment sends 802.3-framed broadcasts or that any frame was decrypted): group frames
of the delivered class flagged LLC mismatch during the data phase are discarded and
counted, the data phase ends by its budget, and the cleanup follows — the
deauthentication completed, both removal commands credited, any after-removal group frames
discarded under 0177, cleanup stages 1 to 3, no footer: the first healthy C3 lifetime of
the series. The beacon total with its keyed part, the data-phase LLC-discard total and the
cleanup-discard total are recorded at stage 3; the lease, the ping replies and the laptop's
Wi-Fi SSH exchange are observed again and reported apart; none is implied by another.

Unique measurements: the data-phase `data LLC mismatch discarded` records (first eight,
numbered by their descriptor and type or length word) and `data LLC mismatches discarded:
total`; the `beacon delivered` records and `beacons delivered: total ... keyed`; the
`cleanup group frame discarded` records and total if 0177's class arrives; the data phase's
end record and reason; the completions by PID; the deauthentication's completion, the key
removal commands and their credits, the cleanup submissions 0 to 2 and the stage-3 record;
any footer's status and branch; the session's `udhcpc`, `ping` and the laptop's Wi-Fi SSH
receipt bound to `mainline_boot`, each reported as what it is.

Branches, each ending the lifetime exactly once:

1. The data phase runs to its budget, then the cleanup records stages 1 to 3 without a
   footer: 0178 observed if any data-phase LLC discard was recorded (unobserved if none
   arrived); 0177 observed if any after-removal discard was recorded; the first healthy C3
   lifetime of the series; the network terms decide the next direction individually.
2. A refusal of another shape inside the data phase or the cleanup: recorded by its
   descriptor and header fields, fail-stop, seal, reviewed native recovery once; the next
   decision is taken from those fields, not by broadening on the device.
3. A disconnect, or a branch-9 footer: read from the supplicant fields and the delivered
   beacon records, as runtime 30's branches state (a data-end record printed by a later
   supplicant teardown on an already-stopped lifetime is a consequence, not a cause).
4. Any other named refusal or fault (a frame-gate refusal elsewhere, a key refusal, a data
   TX timeout, the grant too close to its end, the packet budget): fail-stop as before,
   seal, reviewed native recovery once.

No branch repeats a boot without a decision-changing change. Nothing is reconnected or
rekeyed. No Wi-Fi operational, reliability or replay-protection claim follows from any
branch; `wifi_operational` stays false; replay protection remains unproven and unclaimed.

## Bindings

| Adapter | Runtime 31 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 8ccf249c…`, `PACKAGE bfa7516a…` (7d7d813d); every other pin unchanged |
| `install-passive.py` | predecessor `27005b8f…` (installed candidate 29), receipt `mt6797-wifi-phase-b-deployment-30`, `results/candidate-30.json`, slot `44117611…` |
| `capture-private.py` | `capture-31`, `session-31/deployment-summary.txt`, `results/candidate-30.json`, slot `44117611…` |
| `passive-session.py` | `results/candidate-30.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-31`, `capture-31`; identity `runtime-31/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-30.json` against the compile-35 input and package, both slots, predecessor `27005b8f…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-31` only |
| `join-once.sh`, `laptop-wifi-ssh.py` | unchanged from runtime 30 |

## Evidence and claims

As in runtimes 21 to 30: the sealed kernel log classified by `classify-join.py`, the
session's fixed fields and phrase counts, the private supplicant log digested (the
disconnect fields extracted locally if any), the laptop's Wi-Fi SSH receipt bound to
`mainline_boot`. Runtime 30's original evidence and verdicts stay intact. No RE, replay or
radio test is authorized for this change; the pinned vendor headers and source suffice.
