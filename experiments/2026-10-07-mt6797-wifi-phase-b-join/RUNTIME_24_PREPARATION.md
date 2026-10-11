# Runtime 24 preparation: the runtime 23 protocol on candidate 23 (proposal 0170)

Status: candidate 23 composed and validated by the custodian at b6f433d1 from the
compile-28 package `4d9372a7…` (input c9781bea, proposals 0163 to 0170) with
candidate 22's RAM root byte-identical (`449832a3…`), the same board DT
`25ab60f4…` and kernel config `975f8703…` (the custodian compared all three byte
for byte; the helper and supplicant are unchanged; the PSCI and clock flags are
preserved by the validated composer); boot image `c7e2e345…` (12302336 bytes), full
padded boot2 `1b07a2bb…`. [results/candidate-23.json](results/candidate-23.json)
(SHA-256 `df97152a…`) is the receipt's exact bytes and
`runtime-24/results/candidate.json` its copy. The current boot2 content is the
installed candidate 22 (`419797dd…`); the known-good stock boot is `89d49b95…`.
The custodian rederives the live GPT and verifies the predecessor with the
reviewed guard at deployment; the custodian remains the sole device custodian.
No device step has run.

## What differs from runtime 23

- Kernel, proposal 0170 only: the key command's credit waiter owns exactly its
  pending completion (the worker's cleared flag, under the worker's own credit
  deadline) and no longer consults the shared page debt; a key command refused
  while the lifetime runs ends it synchronously through the worker's one terminal
  path (footer, branch 8) instead of retiring without a record; a stop found for an
  externally raised error reports that error as the footer's status.
- Host wrapper, one explicit change: `join-once.sh` prints one `keepalive=<tick>`
  line every 20 ticks inside its wait so the USB listener's 60 s idle timeout
  cannot close the join phase during the 100 s wait (runtime 23's session closed
  at about 60 s). It is a fixed field line and nothing else about the wrapper,
  the data checks, the listener or the laptop helper changes.
- Everything else, including every key, class, data and radio budget, the scoped
  commands, the 0168 and 0169 hypotheses and branches, the session tools and the
  bindings, is [RUNTIME_23_PREPARATION](RUNTIME_23_PREPARATION.md)'s, with runtime
  24, capture 24, session 24 and deployment 23 in their place. One test only, with
  the reviewed recovery once.

## Hypothesis, unique measurement and branches for 0170

Hypothesis: with message 4 queued or in flight when the supplicant installs the
pairwise key, the command's credit returns and the command completes (the
`key credit returned: pairwise` record follows the `key command: pairwise
submitted` record whether message 4 goes out before or after it); the group key
then follows and the runtime 21 hypothesis applies from there.

Unique measurements: the order of the `key command: pairwise submitted`, `credit`,
`eapol sent: pid=4`, `key done: first after=pairwise` and `key credit returned:
pairwise` records, and the absence of a `key command refused: pairwise ...
running=1` record; the classifier's `key_credits_returned`. The credit's
attribution to the command remains by order; the add-key-done event remains
attributed by window only.

Branches, each ending the lifetime exactly once:

1. The pairwise credit returned and the command completed with message 4 queued
   or in flight (either order of the eapol-sent and credit records): the 0170
   case is recorded as observed and the runtime 21 branches decide the rest.
2. The pairwise credit returned and the command completed with message 4 already
   acknowledged before the key arrived (runtimes 20 to 22's ordering): 0170's
   ordering is unobserved in this boot and nothing about it is claimed beyond its
   fixtures; the runtime 21 branches decide the rest.
3. A key command refused while the lifetime runs (any status): the footer with
   that status and branch 8 follows at once, the lifetime fail-stops, the device
   script sees the terminal record and seals; recorded as a refusal with a
   terminal failure, not malformed. No retry.
4. A key command refused with the lifetime already stopped (runtime 16's shape):
   recorded as before, no second footer.

No branch repeats a boot without a decision-changing change. Nothing is
reconnected or rekeyed. No replay-protection or operational claim follows from any
branch.

## Bindings

| Adapter | Runtime 24 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT c9781bea…`, `PACKAGE 4d9372a7…`; every other pin unchanged |
| `install-passive.py` | predecessor `419797dd…` (installed candidate 22), receipt `mt6797-wifi-phase-b-deployment-23`, `results/candidate-23.json`, slot `df97152a…` |
| `capture-private.py` | `capture-24`, `session-24/deployment-summary.txt`, `results/candidate-23.json`, slot `df97152a…` |
| `passive-session.py` | `results/candidate-23.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-24`, `capture-24`; identity `runtime-24/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-23.json` against the compile-28 input and package, both slots, predecessor `419797dd…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-24` only |
| `join-once.sh` | the keepalive line every 20 ticks; otherwise as runtime 23 |

## Evidence and claims

As in runtimes 21 to 23: the sealed kernel log classified by `classify-join.py`,
the session's fixed fields and phrase counts (the keepalive lines are ignored by
the field parser), the private supplicant log digested, the laptop's Wi-Fi SSH
receipt bound to `mainline_boot`. `wifi_operational` stays false; a lease, ping
replies and the boot-bound SSH exchange are the only network-function evidence
and are reported as such.
