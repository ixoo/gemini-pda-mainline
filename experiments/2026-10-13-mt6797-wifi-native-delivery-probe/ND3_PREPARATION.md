# ND3 — operation-deadline successor (not yet a device result)

Kernel inputs: `985744adb169ea543d5a8963cf710878c4dc9125`, profile
`mt6797-a53-wifi-native-delivery-diag`. Source review accepted the exact
0185 patch digest
`c38b4834f0032e052f0ef26091471c76b72b4a2e1551e4ec7d74b6df67eb1b16`.
Pending maintained 0184 corrections are excluded from this kernel.

The managed Buildbox-1 build and package validation passed (32 jobs):
inventory `fd232eaf39f501db4e6c6c81c40953acfce95dadded1dd3f29275c5ef994d4a2`,
Image.gz `dd56fddd5d5647d0439f79725d8176a63238d82db7d8af76265809111595bcc0`,
resolved config `33a50989755c6e226e3a4f388177d35956d407702f4e08120e737f28d6b2bf43`.
All 681 selected patches replayed in canonical order. Actual native caller/HIF
and existing native decision/loop/RX tests passed against the built source.
Compilation reported an existing unrelated unused CPU-hotplug inventory
function and an inherited patch-application whitespace warning; no build error.
No new DT or configuration change was made; DT schema validation was not rerun.
No device action or native firmware observation has occurred for ND3.

## Real composition and fresh runtime bindings

The laptop custodian ran the committed `bdff094b` compositor. All composition,
inventory/provenance/configuration, 64-member RAM-root and LK gates passed;
independent six-file hash/size and exact 16 MiB zero-padding checks passed.
DT, config and RAM root are byte-identical to ND2; only the kernel changed.

- [Real candidate receipt](results/native-delivery-candidate-3.json):
  `f00de1e3bcc40e912ba65f7ebbe3ad15bbc159b230f3e84af3b45dd8cebe7e10`.
- Raw boot: `e25c1fa387f2be84908363a4e65f7e4b70ffea541684bccd991a4736f44980a6`,
  12668928 bytes. Candidate directory must be `candidate-` plus this full digest.
- Full boot2: `7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06`,
  16777216 bytes. This is composition evidence, not a deployment receipt.

Use a fresh private `GEMINI_RUNTIME_ROOT` (runtime-3), the retained private
`GEMINI_PRIVATE_REPO` and PSK-bound `GEMINI_JOIN_SCRIPT` wrapping unchanged
`join-native.sh`. No credentials or private RAM-root members are published.

| Program/identity | ND3 binding |
| --- | --- |
| `prepare-native-delivery-3.py` | Checks real receipt pin; creates only `native-delivery/session-nd3`, leaves `capture-nd3` absent for one-attempt claim |
| `install-native-3.py` | Real receipt, ND2 predecessor, actual program digest, deployment name `mt6797-wifi-native-delivery-deployment-3`; unchanged source/GPT/root/power/write/readback/shutdown guards |
| `laptop-capture-native-3.py` | Real receipt, `capture-nd3`, `session-nd3/deployment-summary.txt`; unchanged Phase-A capture gates |
| `passive-host-native-3.py` | `session-nd3`/`capture-nd3`, exact `runtime-nd3/results/candidate.json` copy, helper output identity |
| `laptop-session-native-3.py` | Actual prepare/check_ram_root namespace selects ND3; required C32 supplicant/wpa_cli checks retained; actual installer routed to ND3 |

ND2's scripts, receipt and evidence are not edited. The shared native classifier,
Wi-Fi helper and one-cycle join script remain unchanged. The wiring test loads
the actual modules/namespaces, checks installer derivation with its own digest,
exercises offline preparation/fresh-root refusal and bad-candidate refusal.
It makes no device call and creates no deployment receipt. Classifier and Wi-Fi
helper fixtures also pass; a full private-candidate dry run remains with the
custodian before installation. No installed or booted ND3 claim is made.

## Hypothesis and unique observation

ND1 and ND2 both refused locally before PIO. ND3 changes only the shared native
enable/disable operation deadline to the existing 100 ms budget capped by the
remaining lifetime. The unique question is whether the real device gets beyond
that host refusal and supplies a native-mode datum. Passing host tests or a
build is not an answer. No command retry or firmware acceptance is inferred
from credit retirement.

The [bounded diagnostic protocol](NATIVE_DELIVERY_PROBE.md) remains unchanged:
one association lifetime, finite native capture and retirement, no guard,
radio, credit, HIF or recovery-budget expansion. All source, package, candidate,
boot, seal and helper identities must match before their corresponding stage.

## Decision branches

- Local submit failure/expiry or poison: preserve exact status and ledger
  evidence; firmware mode remains untested. Diagnose the changed failure
  before proposing another candidate; do not retry unchanged artifacts.
- Submitted/retired enable but no eligible native delivery: record transport
  ownership separately from firmware semantics; no supported-mode verdict.
- Eligible native MPDUs but no authenticated post-ACTIVE challenge: preserve
  the partial observation, withhold a usable station/crypto claim.
- Eligible native delivery plus verified boot-bound post-ACTIVE challenge:
  this meets only the diagnostic predicate. It does not establish hostile
  replay rejection, sustained traffic, rekey, reuse, IRQ/DMA, or maintained
  driver completion. Use it to select the standard host authentication path.
- Any preservation/quiescence/identity failure: stop the affected stage,
  preserve available evidence and defer recovery if its reviewed gates fail.

## Composition and handoff

Use only the validated package for the exact kernel input, byte-identical C32
board DT and private 64-member RAM root with the native release gate. Fresh
ND3 receipt, runtime, capture and session bindings must not reuse ND2 outputs.
The private parent lives with the laptop custodian; the compositor takes no
device action and the custodian returns the real receipt for publication/pins.
No candidate/deployment checksum is invented before that operation. Run
`build-native-candidate-3.py` with `--kernel-package`, `--parent` and a fresh
`--output`; the complete frozen ND2 composition gates remain in force with
only the validated new kernel/package pins rebound.

The installed predecessor is ND2 full boot2
`306ca76fb3136ec96f369bdce72ccbce52a10bd4b05d99f5b763938e551bc533`;
the custodian must rederive and verify it against the live GPT at deployment.
Guarded write/readback and clean shutdown precede owner-operated physical boot2
selection. Only the laptop custodian performs capture, session and the one
reviewed recovery; workers perform no device actions.

[ND2](ND2_RESULT.md) is complete-negative and immutable. Current independently
confirmed return is Gemian `8dc27f98-f95e-4f74-9c4d-d57fd96a613a`. A later
device stage requires fresh live identity, not this historical boot as proof.
