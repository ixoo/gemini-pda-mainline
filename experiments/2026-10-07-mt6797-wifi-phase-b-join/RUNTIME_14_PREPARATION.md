# Runtime 14: the corrected supplicant invocation on the installed candidate 13

Status: candidate 13 remains installed (deployment 13, full padded boot2
`ec412ce9…`, unchanged); no new candidate, build or installation. The device
is in changed-boot Gemian `b20fea57…` after runtime 13's reviewed recovery.
The custodian regenerates the private PSK-bound script from the corrected
`join-once.sh`, prepares fresh `capture-14` and `session-14` evidence roots
(runtime 13's roots are consumed and preserved), and the owner starts boot2
physically; the frozen laptop wrappers then run once each.

## What differs from runtime 13

Exactly one thing: the supplicant is started without `-f` (which the pinned
static build does not implement) and its debug stream and stderr are
redirected into the private RAM log; see [RUNTIME_13](RUNTIME_13.md). The
kernel (compile 18, proposal 0157), the candidate, the installed boot2, the
supplicant binary, the configuration template, the session, host, classifier
and export tooling are unchanged. The pinned binary under QEMU initialises and
reads its configuration with the corrected arguments.

## Hypothesis, unique observation and branches

The hypothesis and branches are those of
[Phase C2](PHASE_C.md#device-protocol-stated-in-advance) with proposal 0157:
the supplicant's one passive channel-40 scan, open-system authentication and
RSN association (capabilities 0x000c admitted), the two EAPOL frames each
way, the two key commands with their credits, the hold, the driver's
deauthentication, the two key removals and the three-stage teardown. Unique
observation: the driver's `eapol delivered`, `eapol sent`, `key command …
submitted`, `key credit returned` and `key removal … submitted` records with
the final cleanup stage, the supplicant's fixed phrases (one scan result set,
key negotiation completed, connected) and the complete private log export
with the byte count the join reported. Branches: the conjunction holds and
runtime 14 passes C2 (no installed-key or operational claim); the supplicant
starts but does not complete (its phrases and the driver records decide, the
healthy teardown runs at the hold's end); a key command is refused or its
credit ambiguous or late (fail-stop); a scan or association shape is refused
(named refusal, now including the RSN capability value); the supplicant fails
to start again (its log, now present, names why); or the AP's behaviour
differs. No branch repeats a boot without a decision-changing change.

## Bindings

| Adapter | Runtime 14 binding |
| --- | --- |
| `install-passive.py` | unchanged (deployment 13 consumed; no new installation) |
| `capture-private.py` | `capture-14`, `session-14/deployment-summary.txt`, `results/candidate-13.json`, slot filled |
| `passive-session.py` | unchanged: `results/candidate-13.json`, 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-14`, `capture-14`; identity `runtime-14/results/candidate.json`, a byte copy of the candidate-13 receipt |
| `prepare-runtime.py` | `results/candidate-13.json`, both slots, predecessor `1c491341…`, the PSK-bound script; creates `wifi-phase-b/session-14` only and leaves `capture-14` absent; deployment receipt `deployment-13` |
| `join-once.sh` | supplicant without `-f`, stdout and stderr into the private 0600 RAM log |
