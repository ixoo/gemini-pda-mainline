# Runtime 28 preparation: the runtime 27 protocol on candidate 27 (proposal 0174)

Status: candidate 27 composed and validated by the custodian at f96049e7 from the
compile-32 package `e9610ba5…` (built input 5ee1f55f, proposals 0163 to 0174) with
candidate 26's RAM root, board DT and kernel config byte-identical (`449832a3…`,
`25ab60f4…`, `975f8703…`; helper, supplicant, PSCI and `clk_ignore_unused`
preserved); boot image `be5e864a…`, full padded boot2 `c45503fa…` (exact 16 MiB).
[results/candidate-27.json](results/candidate-27.json) (SHA-256 `03ee185b…`) is the
receipt's exact bytes and `runtime-28/results/candidate.json` its copy. The current
boot2 content is the installed candidate 26 (`e322e068…`); the stock boot verified
live by the custodian is `57c5ae6e…` (reverified at deployment). The custodian
rederives the live GPT and verifies the predecessor with the reviewed guard at
deployment; the generated installer, the device guard, the full readback, the clean
shutdown, the identity checks, the native recovery and the full-log seal are unchanged
except for these identity bindings. The custodian remains the sole device custodian;
the owner selects boot2 physically. No device step has run.

## What differs from runtime 27

Kernel, proposal 0174 only: the clear broadcast Action class named in runtime 21 (its
decoder unchanged) is counted without a cap of its own; every match is discarded,
never delivered or interpreted, no new host submission; the first eight are recorded
by their descriptor and header fields as before and the total is recorded before the
stage-3 record when it exceeds eight. The lifetime's existing receive budget (32768
packets) bounds the class as it bounds the clear and keyed beacons; the directed
Action class keeps its own eight; no radio, time, TX, credential, ping or SSH budget
changes. The classifier change reviewed with it (data completions bound to the first
recorded submission and the serialized PID order, end counters reconciled, the 0174
total record) reads the sealed log; it changes no device behaviour. Everything else
is [RUNTIME_27_PREPARATION](RUNTIME_27_PREPARATION.md)'s, with runtime 28, capture
28, session 28 and deployment 27 in their place. One test only, with the reviewed
native recovery once after the evidence is sealed.

## Hypothesis, unique measurements and branches

Hypothesis (a next-runtime hypothesis; runtime 27's stop cause remains a
source-supported inference): frames of the 0168 class keep arriving past the eighth
and are discarded and counted under the existing packet bound instead of refused, so
the data phase inside the grant runs to its budget or to the supplicant's disconnect
and the cleanup stages are reached. The data completions, the lease, the ping
replies, the laptop's Wi-Fi SSH exchange and the healthy cleanup are observed and
reported separately; none is implied by another.

Unique measurements: the eight `group action frame discarded` records and, if more
arrive, `group action frames discarded: total=<n>` before the stage-3 record (the
classifier reports the total and the record count apart); the data phase's end
record and its reason; the data completions by PID with status 0 and non-zero apart
(a completion is not an acknowledgement or a delivery); the `data credit` chronology;
any late completion; the three cleanup stages. The session's `udhcpc`, `ping` and the
laptop's Wi-Fi SSH receipt remain the only network-function evidence, each reported
as what it is.

Branches, each ending the lifetime exactly once:

1. The class arrives past eight, counted, no refusal; the data phase ends by budget or
   disconnect and the cleanup stages are recorded: 0174 observed; the network terms
   decide the next direction individually (a lease without ping replies, or replies
   without the SSH exchange, are separate negative results, not a fault of 0174).
2. Eight or fewer of the class in this boot: 0174 unobserved; the data phase and the
   network terms decide as in branch 1.
3. A frame of the same descriptor shape refused at the frame gate even so: the
   decoder's source-defined conditions did not hold for it; recorded by the refusal's
   fields; fail-stop, seal, reviewed native recovery once; the next decision is taken
   from those fields, not by broadening on the device.
4. Any other named refusal or fault (a ninth directed Action discard, a neighbouring
   shape, a key refusal, a data TX timeout, the grant too close to its end, the
   32768-packet budget): fail-stop as before, seal, reviewed native recovery once.

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed. No replay-protection or operational claim follows from any
branch.

## Bindings

| Adapter | Runtime 28 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 5ee1f55f…`, `PACKAGE e9610ba5…` (f96049e7); every other pin unchanged |
| `install-passive.py` | predecessor `e322e068…` (installed candidate 26), receipt `mt6797-wifi-phase-b-deployment-27`, `results/candidate-27.json`, slot `03ee185b…` |
| `capture-private.py` | `capture-28`, `session-28/deployment-summary.txt`, `results/candidate-27.json`, slot `03ee185b…` |
| `passive-session.py` | `results/candidate-27.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-28`, `capture-28`; identity `runtime-28/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-27.json` against the compile-32 input and package, both slots, predecessor `e322e068…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-28` only |
| `join-once.sh`, `laptop-wifi-ssh.py` | unchanged from runtime 27 |

## Evidence and claims

As in runtimes 21 to 27: the sealed kernel log classified by `classify-join.py`
(which knows the 0174 total record and binds the data completions), the session's
fixed fields and phrase counts, the private supplicant log digested, the laptop's
Wi-Fi SSH receipt bound to `mainline_boot`. `wifi_operational` stays false; a lease,
ping replies and the boot-bound SSH exchange are the only network-function evidence
and are reported as such. Runtime 27's original evidence and verdicts stay intact.
