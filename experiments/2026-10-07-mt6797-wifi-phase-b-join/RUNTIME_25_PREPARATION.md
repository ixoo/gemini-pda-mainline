# Runtime 25 preparation: the runtime 24 protocol on candidate 24 (proposal 0171)

Status: candidate 24 composed and validated by the custodian at 486947dc from the
compile-29 package `0ce04178…` (input 1057b6b5, proposals 0163 to 0171) with
candidate 23's RAM root byte-identical (`449832a3…`), the same board DT
`25ab60f4…` and kernel config `975f8703…` (all three byte-compared by the
custodian; every other file checksum reverified; only the kernel image, boot image
and padded partition differ; helper, supplicant, PSCI and clock flags unchanged);
boot image `e87df8c1…` (12300288 bytes), full padded boot2 `35014d84…`.
[results/candidate-24.json](results/candidate-24.json) (SHA-256 `b6d3689e…`) is the
receipt's exact bytes and `runtime-25/results/candidate.json` its copy. The current
boot2 content is the installed candidate 23 (`1b07a2bb…`); the known-good stock
boot is `40295547…`. The custodian rederives the live GPT and verifies the
predecessor with the reviewed guard at deployment; the custodian remains the sole
device custodian. No device step has run.

## What differs from runtime 24

Kernel, proposal 0171 only: runtime 18's directed clear Action class is also
discarded in its keyed descriptor variant (security mode 4, status 0xe004) once
the pairwise key is installed, within the same shared eight-per-lifetime budget;
the unkeyed variant stays admitted as before; mixed pairs and the keyed variant
before the key are refused; nothing of that class is delivered. The host wrapper
(with its keepalive line), the laptop helper and its bounds, every key, class,
data and radio budget, the scoped commands, the 0168 to 0170 hypotheses and
branches, the session tools and the bindings are otherwise
[RUNTIME_24_PREPARATION](RUNTIME_24_PREPARATION.md)'s, with runtime 25, capture 25,
session 25 and deployment 24 in their place. One test only, with the reviewed
native recovery once after the evidence is sealed.

## Hypothesis, unique measurement and branches for 0171

Hypothesis: after the pairwise key's credit the target's directed clear Action
frame recurs in its keyed descriptor variant, is discarded and recorded within the
shared budget, the supplicant's group key command is then submitted and credited,
and the runtime 21 hypothesis applies from there (channel release, data phase,
DHCP, ping, the Wi-Fi SSH exchange, teardown).

Unique measurements: the `action frame discarded` records with `sec=4
status=0xe004` and their counts, placed after `key credit returned: pairwise` and
before the group key command; the onward records (`key command: group submitted`,
its credit, `channel released`, `data phase`); the classifier's
`action_frame_discards`. Nothing about the frame's category, body, BSSID or
sequence is measured or claimed.

Branches, each ending the lifetime exactly once:

1. One to eight directed Action discards in either variant after the pairwise key
   (each recorded with its security mode and status), then the group key command
   and its credit: the 0171 case is recorded as observed with its counts and the
   runtime 21 branches decide the rest.
2. No such frame after the pairwise key: the class is unobserved in this boot and
   nothing about it is claimed beyond its fixtures; the runtime 21 branches decide
   the rest.
3. A ninth frame of the class, or a frame of a neighbouring shape (a mixed
   security-mode and status pair, the ICV-error flag, a protected frame control,
   another peer, another index): a refusal at the frame gate, fail-stop, seal,
   reviewed recovery; recorded by the refusal's descriptor fields; no broadening
   on the device.
4. Any other named refusal or fault: fail-stop as before, seal, reviewed recovery.

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed. No replay-protection or operational claim follows from any
branch.

## Bindings

| Adapter | Runtime 25 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 1057b6b5…`, `PACKAGE 0ce04178…`; every other pin unchanged |
| `install-passive.py` | predecessor `1b07a2bb…` (installed candidate 23), receipt `mt6797-wifi-phase-b-deployment-24`, `results/candidate-24.json`, slot `b6d3689e…` |
| `capture-private.py` | `capture-25`, `session-25/deployment-summary.txt`, `results/candidate-24.json`, slot `b6d3689e…` |
| `passive-session.py` | `results/candidate-24.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-25`, `capture-25`; identity `runtime-25/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-24.json` against the compile-29 input and package, both slots, predecessor `1b07a2bb…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-25` only |
| `join-once.sh`, `laptop-wifi-ssh.py` | unchanged from runtime 24 (keepalive line, helper bounds) |

## Evidence and claims

As in runtimes 21 to 24: the sealed kernel log classified by `classify-join.py`,
the session's fixed fields and phrase counts, the private supplicant log digested,
the laptop's Wi-Fi SSH receipt bound to `mainline_boot`. `wifi_operational` stays
false; a lease, ping replies and the boot-bound SSH exchange are the only
network-function evidence and are reported as such.
