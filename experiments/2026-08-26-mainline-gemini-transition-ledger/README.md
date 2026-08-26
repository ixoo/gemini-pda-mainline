# Mainline Gemini retained transition ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-gemini-transition-ledger` |
| Status | complete hardware-free Buildbox and QEMU proof; physical integration pending |
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
- [`scripts/run-kunit-qemu`](scripts/run-kunit-qemu) verifies the exact package
  and runs one bounded arm64 QEMU boot with networking disabled.
- [`scripts/classify-kunit.py`](scripts/classify-kunit.py) accepts only the
  named six-case suite and expected post-test root-filesystem panic.

## Planned procedure

1. Generate and review one production-owner patch and one test patch on the
   exact prepared source.
2. Admit them to the canonical series with one focused profile.
3. Compile that exact clean commit on Buildbox.
4. Run the sole six-case suite in bounded no-network arm64 QEMU.
5. Record sanitized evidence before moving to the platform-effect owner.

## Generation and admission

Exact clean commit `439d4c49` generated two normal patches from prepared-source
state `f84562a7`. Both passed strict Checkpatch, production/test source
validation, exact replay, and package checksum validation. The admitted patch
hashes and zero-effect boundary are recorded in
[`results/patch-generation-439d4c49.txt`](results/patch-generation-439d4c49.txt).

Canonical patches `0388` and `0389` now contain the default-off owner and its
six in-memory cases. The first Buildbox compile at `cb18db0a` rejected six
calls through an ops member named `barrier`, because that token collided with
arm64's function-like `barrier()` macro. The exact diagnostic and zero-device
boundary are recorded in
[`results/build-attempt-cb18db0a.txt`](results/build-attempt-cb18db0a.txt).

Clean pushed commit `18d401f4` reconstructed the exact through-`0387` parent by
reversing the admitted `0389` and `0388` patches in a bounded temporary file
set, then regenerated the pair with the callback named `sync`. Strict
Checkpatch, production/test validation, exact replay, and package checksums all
passed. The replacement hashes are recorded in
[`results/patch-regeneration-18d401f4.txt`](results/patch-regeneration-18d401f4.txt).

At that checkpoint the corrected focused profile had not yet compiled, so the
regeneration alone supported no runtime or hardware-support conclusion. No
retained memory, watchdog, CPU, device, or partition was accessed.

## First compile and QEMU result

Exact pushed commit `1660cb1e` compiled and passed complete package validation
on Buildbox. Its single no-network QEMU suite passed all six cases with the
expected post-test root-filesystem panic. This proves the injected in-memory
owner contract, not the physical Gemini mapping or a production caller. Exact
hashes and case results are in
[`results/build-qemu-1660cb1e.txt`](results/build-qemu-1660cb1e.txt).

That build also emitted six new `-Wframe-larger-than` warnings, all caused by
two 256-entry write-history arrays in the test fixture. Only the last write was
asserted. Commit `7d61de24` replaced those arrays with two last-write fields,
removed no assertion, and regenerated the exact test patch. Strict Checkpatch,
source validation, replay, package checksums, and the 145-profile invariant all
passed; see
[`results/patch-regeneration-7d61de24.txt`](results/patch-regeneration-7d61de24.txt).
The exact stack-clean replacement at pushed commit `de9f35ef` compiled on
Buildbox and passed complete package validation. It emitted no transition-ledger
or test-fixture warning; the warning inventory contains only the inherited
unused CPU helper and known patch `0261` whitespace notice. The fetched exact
package then passed the sole bounded, no-network QEMU suite: all six named
cases passed with zero failures or skips. Exact build, artifact, warning, and
runtime identities are recorded in
[`results/build-qemu-de9f35ef.txt`](results/build-qemu-de9f35ef.txt).

This closes the mutable retained-ledger hardware-free milestone. It proves the
default-off injected state machine, alternating-copy recovery, rejection
rules, and one-shot terminal behavior. It does not prove the physical retained
RAM mapping or any production caller; no device was accessed and no boot
candidate was created.
