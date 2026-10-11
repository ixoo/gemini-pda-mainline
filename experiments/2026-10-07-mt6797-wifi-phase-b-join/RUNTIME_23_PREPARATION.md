# Runtime 23 preparation: the runtime 22 protocol on candidate 22 (proposal 0169)

Status: candidate 22 composed and validated by the custodian at 861948f7 from the
compile-27 package `d1cbc042…` (input 85cbc78f, proposals 0163 to 0169) with
candidate 21's RAM root byte-identical (`449832a3…`), the same board DT
`25ab60f4…` and kernel config `975f8703…`; boot image `caf90adf…` (12300288
bytes), full padded boot2 `419797dd…`. [results/candidate-22.json](results/candidate-22.json)
(SHA-256 `35f96d49…`) is the receipt's exact bytes and
`runtime-23/results/candidate.json` its copy. The current boot2 content is the
installed candidate 21 (`79cde346…`); the known-good stock boot is `720fcced…`.
The custodian rederives the live GPT and verifies the predecessor with the
reviewed guard at deployment; the custodian remains the sole device custodian.
No device step has run.

## What differs from runtime 22

Only proposal 0169: the protected group-addressed data class of runtime 17
(`group-data.h`) is named by the broadcast WLAN entry the station record declares
(2 since proposal 0164) instead of the literal 0 runtime 17 measured under the
earlier declaration; every other condition, the pre-group-key window and the
sixty-four-per-join budget are unchanged. The protocol, limits, session tools,
the 0168 hypothesis and branches, and the bindings are otherwise
[RUNTIME_22_PREPARATION](RUNTIME_22_PREPARATION.md)'s, with runtime 23, capture
23, session 23 and deployment 22 in their place.

## Hypothesis, unique measurement and branches for 0169

Hypothesis: the packet that ended runtime 22 after message 4 recurs, is the full
class on the decoder's checks (the target as transmitter, a group receiver,
fragment 0, the strict descriptor fields) with WLAN index 2, is discarded and
recorded without delivery as runtime 17's was, and the lifetime continues into
the key commands; the rest of the runtime 21 hypothesis then applies.

Unique measurements: the `group data discarded` records (count, bytes, frame
control, match, WLAN index, BSSID field, security mode, status; never the body or
an address), their placement before the group key's credit, and the classifier's
`group_data_discard_records`.

Branches for the class, each ending the lifetime exactly once:

1. One to sixty-four such frames discarded before the group key's credit, the
   first eight recorded, the key commands submitted and credited: the class is
   recorded as observed with its count and the runtime 21 branches decide the
   rest (zero frames is branch 4).
2. A sixty-fifth such frame, or the same frame after the group key's credit: a
   refusal at the frame gate, fail-stop, seal, reviewed recovery; the count
   stands as the measurement.
3. A frame of a neighbouring shape (WLAN index 0 or any other index, the
   unicast-to-me flag, an unprotected frame control, another status, another
   transmitter, a directed receiver): a refusal as before, recorded by the
   refusal's descriptor fields for a later source-backed decision; no broadening
   on the device.
4. No such frame: the class is unobserved in this boot and nothing about it is
   claimed beyond its fixtures.

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed. No replay-protection or operational claim follows from any
branch.

## Bindings

| Adapter | Runtime 23 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 85cbc78f…`, `PACKAGE d1cbc042…`; every other pin unchanged |
| `install-passive.py` | predecessor `79cde346…` (installed candidate 21), receipt `mt6797-wifi-phase-b-deployment-22`, `results/candidate-22.json`, slot `35f96d49…` |
| `capture-private.py` | `capture-23`, `session-23/deployment-summary.txt`, `results/candidate-22.json`, slot `35f96d49…` |
| `passive-session.py` | `results/candidate-22.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-23`, `capture-23`; identity `runtime-23/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-22.json` against the compile-27 input and package, both slots, predecessor `79cde346…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-23` only |

## Evidence and claims

As in runtimes 21 and 22: the sealed kernel log classified by `classify-join.py`,
the session's fixed fields and phrase counts, the private supplicant log
digested, the laptop's Wi-Fi SSH receipt bound to `mainline_boot`.
`wifi_operational` stays false; a lease, ping replies and the boot-bound SSH
exchange are the only network-function evidence and are reported as such.
