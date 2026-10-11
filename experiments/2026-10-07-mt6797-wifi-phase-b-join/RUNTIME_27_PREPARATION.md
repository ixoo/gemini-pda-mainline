# Runtime 27 preparation: the runtime 26 protocol on candidate 26 (proposal 0173)

Status: candidate 26 composed and validated by the custodian at d148745a from the
compile-31 package `bc0f928e…` (input c7ba623f, proposals 0163 to 0173) with
candidate 25's RAM root, board DT and kernel config byte-identical (`449832a3…`,
`25ab60f4…`, `975f8703…`; helper, supplicant, PSCI and `clk_ignore_unused`
preserved); boot image `99d1d9e7…` (12300288 bytes), full padded boot2
`e322e068…`. [results/candidate-26.json](results/candidate-26.json) (SHA-256
`b969063c…`) is the receipt's exact bytes and `runtime-27/results/candidate.json`
its copy. The current boot2 content is the installed candidate 25 (`b38d25a9…`); the
stock boot reverified read-only by the custodian is `010ae842…`. The custodian
rederives the live GPT and verifies the predecessor with the reviewed guard at
deployment; the generated installer, the device guard, the full readback, the clean
shutdown, the identity checks, the native recovery and the full-log seal are unchanged
except for these identity bindings. The custodian remains the sole device custodian;
the owner selects boot2 physically. No device step has run.

## What differs from runtime 26

Kernel, proposal 0173 only: the target's beacon class in its keyed descriptor variant
(WLAN index 2, security mode 4, status 0xe004) is skipped like every parseable clear
beacon once the group key is installed, counted, the first four recorded and the
total before the stage-3 record; never delivered; no discard budget changes. The
decoder names the observed descriptor fields and the first frame-control byte, and
adds source-defined conditions the runtime 26 diagnostic did not carry (frame
control exactly 0x0080, the broadcast receiver, the BSSID equal to the target,
fragment 0, the 12 fixed body bytes present). Everything else, including 0172's data
phase inside the grant with its TC1 observability, the host wrapper, the laptop helper
and every bound, is [RUNTIME_26_PREPARATION](RUNTIME_26_PREPARATION.md)'s, with
runtime 27, capture 27, session 27 and deployment 26 in their place. One test only,
with the reviewed native recovery once after the evidence is sealed.

## Hypothesis, unique measurements and branches

Hypothesis (a next-runtime hypothesis, not a claim that runtime 26 is resolved): the
target's keyed beacon recurs after the group key, matches 0173's class including its
source-defined conditions, and is skipped and recorded; the first data frame on TC1
is then measured inside the grant as runtime 26 was meant to measure it.

Unique measurements: `keyed beacon skipped: ... count=1..4` and `keyed beacons
skipped: total=<n>` (the classifier's notifications); then 0172's measurements
unchanged, kept apart: the first `data TX` record, its `TX done: pid=<p> status=<s>`
(status 0 and non-zero reported separately; completion is not acknowledgement or
delivery), the `data credit` chronology against the frames (the totals are
cumulative), any `data TX timeout` record read by its own `debt`, the `data phase
end` counters, the three cleanup stages inside the grant. The session's `udhcpc`,
`ping` and the laptop's Wi-Fi SSH receipt remain the only network-function evidence.

Branches, each ending the lifetime exactly once:

1. The keyed beacon skipped and recorded; the first data frame submitted: the 0173
   class is observed and runtime 26's branches 1 to 4 (TX done with credits; TX done
   without an observed return; timeout with the frame's debt 0; timeout with the full
   debt) decide the next direction exactly as written there.
2. No keyed beacon before the first data frame: the 0173 class is unobserved in this
   boot; 0172's measurements decide as in runtime 26's branches 1 to 4.
3. A frame of the target's beacon class whose unmeasured fields differ from the
   source-defined conditions (flag byte, receiver, BSSID, fragment, body length):
   refused at the frame gate as before, recorded by the refusal's descriptor fields;
   fail-stop, seal, reviewed native recovery once; the next decision is taken from
   those fields, not by broadening on the device.
4. Any other named refusal or fault (a ninth directed Action discard, a neighbouring
   shape, a key refusal, the grant too close to its end): fail-stop as before, seal,
   reviewed native recovery once.

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed. No replay-protection or operational claim follows from any
branch.

## Bindings

| Adapter | Runtime 27 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT c7ba623f…`, `PACKAGE bc0f928e…`; every other pin unchanged |
| `install-passive.py` | predecessor `b38d25a9…` (installed candidate 25), receipt `mt6797-wifi-phase-b-deployment-26`, `results/candidate-26.json`, slot `b969063c…` |
| `capture-private.py` | `capture-27`, `session-27/deployment-summary.txt`, `results/candidate-26.json`, slot `b969063c…` |
| `passive-session.py` | `results/candidate-26.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-27`, `capture-27`; identity `runtime-27/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-26.json` against the compile-31 input and package, both slots, predecessor `b38d25a9…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-27` only |
| `join-once.sh`, `laptop-wifi-ssh.py` | unchanged from runtime 26 |

## Evidence and claims

As in runtimes 21 to 26: the sealed kernel log classified by `classify-join.py`
(which knows the keyed-beacon records and the 0172 shape), the session's fixed fields
and phrase counts, the private supplicant log digested, the laptop's Wi-Fi SSH receipt
bound to `mainline_boot`. `wifi_operational` stays false; a lease, ping replies and
the boot-bound SSH exchange are the only network-function evidence and are reported as
such. Runtime 26's original evidence and verdicts stay intact.
