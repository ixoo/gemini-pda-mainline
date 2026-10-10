# Phase C compile 25: proposals 0164 to 0167, C2 completion and the legacy C3 data path

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `84799218b649b4a59358e08ecff4c44a7ea91eea`, clean, the revision
  carrying the custodian's two review rounds on 0166 and 0167 and the 0165 forward
  declaration.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 666 selected patches: the compile-24
  selection plus proposals 0163 to 0167 after 0162, in canonical order; patchset
  `58ee1d79…`, source `be41c068…` unchanged; the package provenance series equals the
  selected series (the four new proposals present).
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend after the
  existing-job, clean-input, capacity, lock and free-space checks; generated
  `2026-10-10T22:02:10Z`, job completed `2026-10-10T22:02:35Z`.
- Attempt 1 at `7422e4a5` failed to compile `mac.c`: the channel release added by 0165
  called the credit wait before its definition, and the host fixture had supplied that
  declaration itself (no object produced; the job status is no record). 0165 now
  declares it next to the other forward declarations; a static scan finds no other
  use-before-definition in `mac.c` or `hif.c`.
- Job: `84799218b649b4a59358e08ecff4c44a7ea91eea-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log SHA-256
  `63bc18a4…`).
- Validated package inventory SHA-256: `cca46f5868b7a443116ce94ff7e5135c6eec2fda2c6fed048446388d9550fc0b`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 24.
- `Image.gz` SHA-256: `ff95005b5785c156f56352b2af8dfe8b54e620d011e92a1500b439dc77353731`
  (decompressed 15960072 bytes, the same as compiles 19 to 24).

The board DT is unchanged (123 DTBs, checksums passed at validation). Warnings against
the documented baseline: exactly the same two pre-existing non-driver lines (the
trailing-whitespace note while applying v7.1.3 patch 0261 and the unused-function
warning in `kernel/cpu.c`); zero MT6797 driver warnings.

## Candidate 20 composition (waits for the custodian's review)

The custodian composes candidate 20 privately with the reviewed composer at the pushed
head: this package with candidate 19's RAM root (its busybox provides the `udhcpc`,
`ping`, `ip` and `timeout` applets and `dropbear`, per the custodian's parse of the
retained parent root), the release gate, the Phase C helper and supplicant unchanged;
the session files `join-once.sh`, `passive-host.py` and `c2-session.py` at this head and
the laptop's `laptop-wifi-ssh.py`; the same board DT and kernel configuration. The
protocol is [RUNTIME_21_PREPARATION.md](RUNTIME_21_PREPARATION.md); the candidate
receipt then binds deployment 20 and runtime 21. No candidate, deployment or device step
has run.
