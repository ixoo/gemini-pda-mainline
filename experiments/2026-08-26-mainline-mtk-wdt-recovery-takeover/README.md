# Mainline MT6797 watchdog recovery takeover

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-mtk-wdt-recovery-takeover` |
| Status | `running` |
| Subsystem | MediaTek MT6797 TOPRGU watchdog |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-26 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, CPU8 physical binding |

## Question or hypothesis

Can the current MediaTek watchdog owner expose one exact, irreversible
15-second recovery takeover that cannot be extended or disabled by later
ordinary watchdog operations, while remaining default-off and fully testable
without MMIO?

## Provenance and environment

- Parent repository commit: `7e065fc946d3cc79b423f8e33ec1a9190c2a2961`.
- Canonical parent series: 377 patches through `0385`.
- Prepared-source state: `66469bd0272084cbf607b068608096ec1e4ea075638393501e758d113e3c7106`.
- Build backend: Buildbox only.
- Boot path and target partition: none in this phase.

## Safety assessment

Patch generation, source validation, compilation, and QEMU tests perform no
watchdog MMIO, device access, retained-RAM write, CPU request, boot-image
assembly, or partition write. The production API has no caller and is disabled
unless its dedicated configuration is selected.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes ownership, register, and refusal semantics.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies deterministic
  production and test edits to the exact prepared source.
- [`scripts/validate_source.py`](scripts/validate_source.py) rejects missing
  gates, extra callers, non-MT6797 reachability, and physical test effects.
- [`scripts/generate-patches.py`](scripts/generate-patches.py) creates normal
  two-patch `git format-patch` output and replays it on the exact parent.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) is the bounded
  Buildbox entry point.

## Procedure

1. Generate a production patch adding the default-off MT6797-only takeover.
2. Generate a separate patch adding five in-memory KUnit cases.
3. Run strict Checkpatch and replay/source validation on Buildbox.
4. Admit the exact patches and a focused profile only after generation passes.
5. Compile on Buildbox and run exactly the named suite in bounded no-network
   QEMU.

## Observations

Pending patch generation.

## Analysis

Pending.

## Conclusion

`inconclusive` until exact patch generation, Buildbox compilation, and the
focused QEMU suite pass.

## Follow-up

After hardware-free proof, connect only the executor's `watchdog_arm` callback.
No physical CPU8 candidate is permitted until the separate retained-stage
ledger and all later physical owners are also proven.
