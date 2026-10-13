# Real candidate35 / runtime36 bindings — offline, not installed

The custodian composed C35 with committed `3b021567` compositor, exact
[compile39](COMPILE_39.md) package and verified real C32 parent. Independent
six-member hashes/sizes, exact 16 MiB zero-padding, package/source/config checks
passed. Config, DT and whole private 64-member RAM root are byte-identical C32;
only the kernel changed. C35 has not been installed or tested on the device.
ND3 remains installed/first; frozen ND3 and C34/R35 tools/receipts are untouched.

## Exact identities

- Kernel input `868ef7217d131daa469e8e866c0f442d77a0c1b5`, phase-b profile.
- Package `ce431869bcaaba805eb4b46bbbb455b3627c07d083123b28bed1bf646e88235c`.
- mac source `ed789fda4fee06ad207e8e76cc17d123dd70b5cfe56d6a6d93ab6d587524fe37`;
  HIF `a6306775ab989767b2780cc4904c1f13019a9e2bcc724fbe459248cd7311996f`.
- [Real receipt](results/candidate-35.json):
  `dcb3db4be44f8fbd6df9ea231de62ec8e6a6c9709dd8e12cb26a6c3c903638a2`;
  exact byte copy at `runtime-36/results/candidate.json`.
- Raw boot `71ff9b549197fc0e5cc252a117a26495d12864eeff37fe950c61e0f2b0636e5b`,
  12666880 bytes. Strict candidate directory is `candidate-` plus full raw digest.
- Full boot2 `ca0af038321e0d6a72ca32c897cffecf158a3a4ee81c4cbf9531d2eb0e99cc21`,
  16777216 bytes; composition, not deployment evidence.
- Installer predecessor is actual installed ND3 full
  `7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06`.
  The custodian must freshly verify Gemian, live GPT, power/inactivity/root and
  full predecessor after completing ND3, before any later installation. An
  offline derived installer with an old boot identity must never be executed.

## Fresh exact bindings

Use a fresh private `GEMINI_RUNTIME_ROOT`, retained `GEMINI_PRIVATE_REPO` and
mode-0600 PSK-bound `GEMINI_JOIN_SCRIPT` with exact unchanged `join-twice.sh`
suffix. No credentials, RAM-root members or deployment receipt are published.

| Program | R36 binding |
| --- | --- |
| `prepare-runtime-36.py` | Requires exact real dcb3 receipt digest and input868/packagece431; creates only `wifi-phase-b/session-36`, refuses reused roots and leaves capture-36 absent for one-attempt claim |
| `install-passive-36.py` | Real C35 receipt, installed ND3 predecessor, actual tool/digest, deployment name `mt6797-wifi-phase-b-deployment-35`; unchanged guarded installer/source pins |
| `capture-private-36.py` | Real receipt pin, capture-36, session-36/deployment-summary.txt; inherited reviewed private baseline/source/claim gates |
| `passive-host-36.py` | Fresh actual host/capture/lower-runtime namespaces, same two-cycle helper output/record; internal adapter, full CLI is laptop session |
| `laptop-session-36.py` | Actual installer routing and shared prepare/check_ram_root namespace selects C35; mandatory C32 supplicant/wpa_cli and source/calibration checks preserved |

The finite two-lifetime protocol, child-group quiescence, capture/session claims,
evidence preservation/sealing, regression and one reviewed recovery are unchanged.
No physical queue substitution or extra observer-only boot is implied. Full
actual private preparation/installer validation/session preflight remains with
the sole laptop custodian; absent real deployment summary must fail closed.
Only an actual guarded installation can create its real deployment receipt.

## Focused checks and limits

`tests/runtime-36-wiring-test.py` loads actual modules/namespaces and checks
receipt copies, all roots/lower-runtime identity, two-cycle helper output,
mandatory RAM tools, actual program/digest/deployment derivation, private capture
baseline, wrong-candidate refusal, exact-digest rejection before any evidence
creation and standalone offline preparation/reused-root refusal. No hardware,
radio, recovery, private-calibration or deployment claim is consumed/fabricated.
The existing R35 wiring regression also passes with its old inputs untouched.
These fixtures are not the actual private-candidate dry run or kernel concurrency.

0186 closes one real terminal regulatory producer gap. Explicit stop is still
terminal, not normal restart support: submitted frame/page and owned peer/key/
channel retirement must be established before any fresh-start admission. No
poison clear, submitted refund, count-as-key-incarnation proof or budget widening.
Native hardware/crypto conclusion waits ND3; IRQ/DMA/status-owner/rekey/reuse,
consolidation and WPA2/DHCP/ping/ten-minute clean-profile SSH remain incomplete.
