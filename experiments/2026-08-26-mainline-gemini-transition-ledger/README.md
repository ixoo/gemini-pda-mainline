# Mainline Gemini retained transition ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-gemini-transition-ledger` |
| Status | implementation and hardware-free proof in progress |
| Subsystem | pstore retained transition evidence |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-26 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, CPU8 physical binding |

## Question or hypothesis

Can one compact, one-shot retained owner preserve the last completed CPU8
transition checkpoint across reset, tolerate a torn replacement, and reject
foreign or out-of-order updates without allocating 18 ramoops records?

## Provenance and environment

- Parent repository commit: `0569f649e2ae8f2a667c6da8ba859cb3d5d553f6`.
- Canonical parent series: 387 patches through `0387`.
- Prepared-source state: `f84562a78968ad20e480ec6ee43533b89f6b9e3491c3c00a9e9da8cbe640ca6d`.
- Build backend: Buildbox only.
- Boot path and target partition: none in this phase.

## Safety assessment

Patch generation, compilation, and QEMU testing use no device and make no
physical retained-memory write. The production API is default-off and has no
caller. The KUnit suite replaces the transport with an in-memory word array.
No boot image or boot candidate is selected.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the one-zone, two-copy wire and state-machine
  contract.
- `templates/` contains the new kernel owner, public/internal interfaces, and
  injected KUnit suite used by deterministic patch generation.
- [`scripts/source_edits.py`](scripts/source_edits.py) applies the production
  and test changes to the exact prepared source.
- [`scripts/validate_source.py`](scripts/validate_source.py) rejects layout,
  sequencing, caller, and hardware-free-boundary drift.
- [`scripts/generate-patches.py`](scripts/generate-patches.py) creates and
  replays two normal format patches.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox) is the bounded
  Git-pinned Buildbox entry point.

## Planned procedure

1. Generate and review one production-owner patch and one test patch on the
   exact prepared source.
2. Admit them to the canonical series with one focused profile.
3. Compile that exact clean commit on Buildbox.
4. Run the sole six-case suite in bounded no-network arm64 QEMU.
5. Record sanitized evidence before moving to the platform-effect owner.

## Current conclusion

Pending hardware-free generation and validation. No retained memory, watchdog,
CPU, device, or partition was accessed.
