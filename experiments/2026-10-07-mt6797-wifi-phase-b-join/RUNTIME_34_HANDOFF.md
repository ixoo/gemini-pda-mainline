# Runtime 34 (Phase-B two-lifetime successor) — composition, install, capture/session CLI

Candidate 33 is the 6d6eabeb Phase-B kernel (proposals 0182/0183) on the verified
last-booted candidate 32: config, board DT and the whole 64-member private RAM
root byte-identical, only the kernel bytes changed. New identity throughout
(candidate 33, session-34, capture-34, deployment-33); candidate 32 / runtime 33
stay pinned (7b2bf45d) and are not retargeted.

## Identity bindings

The reviewed installer, capture, session and host are reused unchanged for
runtime 33 (the default) and select the successor identity only when
`GEMINI_PHASE_B_SESSION=34` is set. The narrow `*-34.py` wrappers set exactly that
and run the reviewed tool; every gate, pin, receipt and private-source remap lives
in the tool. For R34 they resolve to: receipt `results/candidate-33.json`
(sha 064d0f81…), the candidate-32 parent boot2 (5260715b…) as the install
predecessor the reviewed guard verifies against the live GPT, `deployment-33`, and
the `session-34` / `capture-34` roots. Capture and session go through the
laptop-private entries (`laptop-capture.py` / `laptop-session.py`) so the baseline
collector and credentials resolve to the private checkout, not the public one.

## Exact CLI (inspected from the arg parsers; no device write during authoring)

Common env: `GEMINI_PRIVATE_REPO`, `GEMINI_RUNTIME_ROOT`; for capture/session also
`GEMINI_JOIN_SCRIPT` (the private join34 wrapping the reviewed two-lifetime
`join-twice.sh`). `<cand33>` is the composed candidate-33 directory,
`<gemian>` the known-good Gemian boot id (c0534bf5…).

1. Composition (already run; reproducible, offline):
   `./build-successor-candidate.py --kernel-package <linux-7.1.3-gemini-01851f2e… dir> --parent <candidate-32 dir> --output <cand33>`
2. Offline runtime prepare (already run; created session-34, left capture-34 absent):
   `./prepare-runtime-34.py`
3. Installer — generate the derived guard OFFLINE (subcommand `prepare`, which
   writes `install.sh` + `installer.json`, syntax/shellcheck-checked; it does NOT
   write the device). The `-34` wrapper selects candidate 33 for the generation:
   `./install-passive-34.py prepare --previous-gemian-boot <gemian> --candidate <cand33> --output <install-dir>`
   The generated `install.sh` re-invokes this tool's `validate`/`receipt`
   subcommands directly (NOT the `-34` wrapper), which select the candidate by
   `GEMINI_PHASE_B_SESSION` and DEFAULT TO 33 (refusing candidate 33). So root
   executes it with the mode in the environment, which leaves the reviewed
   install.sh source bytes/hash unchanged:
   `GEMINI_PHASE_B_SESSION=34 bash <install-dir>/install.sh`
   It runs under the standing guard, rederiving the live GPT and verifying the
   predecessor (candidate 32, 5260715b). The `validate` and `receipt` subcommands
   are as reviewed for R33 and likewise need `GEMINI_PHASE_B_SESSION=34` when run
   directly for candidate 33.
4. Phase-A capture / one-shot trigger (laptop-private remap; writes
   capture-34/phase-a-result.json):
   `./laptop-capture-34.py --candidate <cand33> --execute`
5. Two-lifetime session over the laptop Wi-Fi/USB path, with the host owning both
   cycles' Wi-Fi SSH checks — set `GEMINI_WIFI_SSH_KEYS` and a fresh verified
   `GEMINI_WIFI_SSH_BOOT` (the mainline boot id; the host then writes
   session-34/wifi-ssh-receipt.json itself):
   `GEMINI_WIFI_SSH_KEYS=<keys> GEMINI_WIFI_SSH_BOOT=<fresh boot> ./laptop-session-34.py --candidate <cand33> --execute`

## Preserved

The updated leaf scripts (negative-scan fatal guard, finite owned-child quiesce,
boot-bound quiescence record), the exporter bytes contract and its transport /
boot / framing / truncation and quiescence recovery gates, the per-life two-cycle
verdict (a healthy two-lifetime is not forced to exit 1 by the single-scan rc),
the private pinned baseline sources, and the single reviewed recovery. No kernel
rebuild and no worker device action; the **owner** performs the physical boot2
selection.
