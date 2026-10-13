# Runtime35 / real candidate34 — bounded station-step preparation

The custodian privately composed candidate34 with committed `2c8c4704`
compositor, real C32 parent and [compile38](COMPILE_38.md) kernel inputs.
All six hashes/sizes and exact 16 MiB zero-padding independently passed.
Config, board DT and the whole private RAM root are byte-identical to C32;
only the kernel changed. No candidate34 installation or runtime is claimed.
ND3 remains installed and first in the device queue; its frozen `d37` executable
pins are untouched.

## Exact inputs and real receipt

- Kernel input: `1edcbfb315f1464e3319aff0be1133b4e948f8e5`;
  profile `mt6797-a53-wifi-phase-b-compile`, no native 0181/0185.
- Validated package:
  `074414c5744a6a45023c136ac3537321c5738b118d4a5a4935b4ad81d613d59e`.
- [Real receipt](results/candidate-34.json):
  `8505a4867cdaaa20d2e9bd687f40958f8ec900ceb7467588e51a7e214cf5b3b3`;
  byte-identical lower runtime copy `runtime-35/results/candidate.json`.
- Raw boot: `d221be19db3f30a2a28f24cd6e9f54a45ff757dfb3595f471eb17fa076685694`,
  12666880 bytes; strict directory basename is `candidate-` plus that full digest.
- Full boot2: `211a42d8051f28054b14a2e7a613293c62f9b0ba40c8308d8a77e7dce3b1b969`,
  16777216 bytes. Composition is not deployment.
- Installed predecessor is ND3 full
  `7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06`;
  rederive/check live GPT and full predecessor at later guarded deployment,
  after ND3's admitted device session. A mismatch refuses; never substitute a
  different partition or silently change the expected predecessor.

## Actual fresh bindings

Use a fresh private `GEMINI_RUNTIME_ROOT`, retained `GEMINI_PRIVATE_REPO` and
mode-0600 PSK-bound `GEMINI_JOIN_SCRIPT` wrapping unchanged `join-twice.sh`.
No credentials, private RAM root or deployment receipt are published here.

| Program | Exact runtime35 identity |
| --- | --- |
| `prepare-runtime-35.py` | Pinned real 8505 receipt/input1ed/package074; creates only `wifi-phase-b/session-35`, leaves `capture-35` absent for claim |
| `install-passive-35.py` | Candidate34, ND3 predecessor, actual tool digest, deployment name `mt6797-wifi-phase-b-deployment-34`; unchanged private-source/GPT/root/power/size/write/readback/shutdown gates |
| `capture-private-35.py` | Candidate34 real pin; `capture-35`, `session-35/deployment-summary.txt`; retained private baseline source with mandatory digests, no source-pin waiver |
| `passive-host-35.py` | Actual session/capture/lower-runtime namespaces and two-cycle helper output/record identity; internal adapter, not a standalone session CLI |
| `laptop-session-35.py` | Full host/private-source binding, actual installer routing and prepare/check_ram_root namespace selecting candidate34; C32 supplicant/wpa_cli remain required |

Existing runtime33/34 and ND1/ND2/ND3 receipts/executables are unchanged.
The adapter imports existing guarded implementation rather than adding a new
installer or orchestration framework. Two-cycle join budgets, helper whole-group
quiescence, evidence/seals, service regression and exactly one reviewed recovery
remain unchanged. The actual private-candidate dry run, fresh live identity and
later deployment/boot identity remain mandatory custodian steps; only the owner
physically selects boot2 after verified installation and clean shutdown.

## Validation and limitations

The focused fixture loads actual modules and shared namespaces; asserts real
receipt copies, all fresh roots, two-cycle helper receipt identity, required
64-member tools, actual installer program/digest/deployment routing, private
capture baseline binding, bad-candidate refusal, offline real-receipt preparation
and reused-root refusal. No device/deployment claim is consumed or fabricated.
The exact actual private candidate is not available to the implementation author;
full private dry run is delegated to the custodian, not claimed by fixtures.

The source and build checks are recorded in compile38. The smaller shared queue
gate protects control admission and may reduce throughput; exceptional hard-cap
drops remain honest drops. The new uncapped owned notifications apply to the
join handler; old scan notification/lifetime budgets remain. General IRQ/DMA,
rekey/reuse, standard authenticated/replay delivery, clean-profile ten-minute SSH
and diagnostic retirement remain full-goal work, not established by this step.

## Later test hypothesis and decision branches

On its later admitted two-lifetime session, correctly formed owned-BSS absence
notifications should hold unsent queue ownership before dequeue, without ending
association solely for absence; presence resumes only when shared pressure clears.
Observe the exact body/phase/count and second-join management/key/data and rearm
chronology; do not borrow another packet's body as R34's unobserved event.

- Second join advances through valid absence/presence and completes bounded
  milestones: demonstrate that station-step scope only, not sustained throughput,
  crypto/rekey/IRQ/DMA or full maintained support.
- Local refusal/failure/timeout: preserve exact boot/candidate/body and ownership
  evidence; distinguish exceptional malformed events, source failure and finite
  budget end before proposing a different change. No unchanged-artifact retry.
- Seal/quiescence/identity failure: stop the affected stage; preserve unique
  evidence and defer recovery if its own reviewed gates fail. No alternate
  recovery or second attempt is inferred from timeout.

No separate observer-only boot or another assembly approval is required by this
preparation. Device actions remain exclusively with the laptop custodian.
