# Runtime 22 preparation: the runtime 21 protocol on candidate 21 (proposal 0168)

Status: candidate 21 composed and validated by the custodian at c33059a0 from the
compile-26 package `dd35c1d2…` (input f53636a3, proposals 0163 to 0168) with
candidate 20's RAM root byte-identical (`449832a3…`), the same board DT
`25ab60f4…` and kernel config `975f8703…`; boot image `df7ee6ef…` (12300288
bytes), full padded boot2 `79cde346…`. [results/candidate-21.json](results/candidate-21.json)
(SHA-256 `62c2f788…`) is the receipt's exact bytes and
`runtime-22/results/candidate.json` its copy. The current boot2 content is the
installed candidate 20 (`d01f3304…`); the stock boot after runtime 21 is
`a2265c06…`. The custodian rederives the live GPT and verifies the predecessor
with the reviewed guard at deployment; the custodian remains the sole device
custodian. No device step has run.

## What differs from runtime 21

Only proposal 0168: the clear broadcast Action frame whose descriptor names no
WLAN table entry (type word 0xee01, descriptor bytes 08 28 18 3c ff 00 00 e0,
first frame-control byte 0xd0, broadcast receiver) is discarded undelivered at any
stage of the lifetime, each one recorded, at most eight per lifetime, the ninth or
any other shape refused. The protocol, limits, session tools and bindings are
otherwise [RUNTIME_21_PREPARATION](RUNTIME_21_PREPARATION.md)'s, with runtime 22,
capture 22, session 22 and deployment 21 in their place.

## Hypothesis, unique measurement and branches for 0168

Hypothesis: the frame that ended runtime 21 after message 4 recurs in the same
environment, is discarded and recorded without delivery, and the lifetime
continues into the key commands; the rest of the runtime 21 hypothesis then
applies (both key credits, channel release, data phase, DHCP, ping, the Wi-Fi SSH
exchange, teardown).

Unique measurements: the `group action frame discarded` records (count, bytes,
descriptor fields; never the body or an address), their placement relative to the
key commands, and the classifier's `group_action_frame_discards`.

Branches for the class, each ending the lifetime exactly once:

1. One to eight such frames discarded, each one recorded, the key commands
   submitted and credited: the class is recorded as observed with its count and
   the runtime 21 branches decide the rest (zero frames is branch 4).
2. A ninth such frame: a refusal at the frame gate (`frame refused`, the same
   descriptor shape), fail-stop, seal, reviewed recovery; the count of eight
   stands as the measurement and the budget is reconsidered from it, not raised
   on the device.
3. A frame of a neighbouring shape (multicast flag, an owning WLAN index, the
   protected bit, a directed receiver, another status): a refusal as before;
   recorded by the refusal's descriptor fields for a later source-backed
   decision; no broadening on the device.
4. No such frame: the class is unobserved in this boot and nothing about it is
   claimed beyond its fixtures.

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed.

## Bindings

| Adapter | Runtime 22 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT f53636a3…`, `PACKAGE dd35c1d2…`; every other pin unchanged |
| `install-passive.py` | predecessor `d01f3304…` (installed candidate 20), receipt `mt6797-wifi-phase-b-deployment-21`, `results/candidate-21.json`, slot `62c2f788…` |
| `capture-private.py` | `capture-22`, `session-22/deployment-summary.txt`, `results/candidate-21.json`, slot `62c2f788…` |
| `passive-session.py` | `results/candidate-21.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-22`, `capture-22`; identity `runtime-22/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-21.json` against the compile-26 input and package, both slots, predecessor `d01f3304…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-22` only |

## Evidence and claims

As in runtime 21: the sealed kernel log classified by `classify-join.py`, the
session's fixed fields and phrase counts, the private supplicant log digested, the
laptop's Wi-Fi SSH receipt bound to `mainline_boot`. `wifi_operational` stays
false; a lease, ping replies and the boot-bound SSH exchange are the only
network-function evidence and are reported as such.
