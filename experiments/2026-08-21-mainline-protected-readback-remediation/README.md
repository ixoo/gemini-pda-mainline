# Protected-readback transport remediation

## Status

Exact Buildbox generation is complete. The three logical patches are generated,
source-validated, replayed exactly, strict-clean, and admitted canonically as
`0316`--`0318`. The isolated Buildbox compile and focused no-network KUnit run
are next; no patch from this experiment has been used on the Gemini.

The first
generation attempt from `b2f0bcddddb1` passed repository checkout, managed
source integrity, and all six pinned source-file identities, then failed closed
in source validation before patch creation. The validator compared the
transport operation against the required-callback check rather than the actual
settle call. The bounded receipt is in
[`results/buildbox-generation-attempt-b2f0bcdd.txt`](results/buildbox-generation-attempt-b2f0bcdd.txt).
The check now selects the call expression explicitly; generated kernel behavior
is unchanged.

The second generation attempt from `dfc5e400ecf4` passed source validation,
generated all three deterministic patches, and reproduced the edited source by
exact replay. Strict checkpatch then rejected patch `0316` with zero errors,
six warnings, and sixteen checks: the raw-string templates emitted one leading
backslash, and several otherwise valid continuations did not use the strict
kernel layout. The bounded receipt is in
[`results/buildbox-generation-attempt-dfc5e400.txt`](results/buildbox-generation-attempt-dfc5e400.txt).
The templates now strip only their leading newline and use shorter internal
helper names plus conventional continuations; transport ordering and effects
are unchanged.

The third attempt from `05ddc25b151a` stopped before patch creation because the
strict-layout edit split the private BigiDVFS fault helper's return type and
name across two lines while the validator retained the old one-line end
anchor. The bounded receipt is in
[`results/buildbox-generation-attempt-05ddc25b.txt`](results/buildbox-generation-attempt-05ddc25b.txt).
The validator now names that exact two-line boundary; kernel source generation
is unchanged.

Generation from `95aa616ed925` again passed source validation, exact three-patch
inventory, and replay. Strict checkpatch reduced patch `0316` to two errors,
two warnings, and two checks, all from three continuation sites. The bounded
receipt is in
[`results/buildbox-generation-attempt-95aa616e.txt`](results/buildbox-generation-attempt-95aa616e.txt).
Two unnecessary production wraps are now single lines and the private-header
prototype uses the same tab continuation as its accepted definition; semantics
remain unchanged.

Generation from `6c473f391ac6` made patch `0316` fully strict-clean and reached
patch `0317`'s first style pass. That patch had zero errors, zero warnings, and
one alignment check at a wrapped private-helper call. The bounded receipt is in
[`results/buildbox-generation-attempt-6c473f39.txt`](results/buildbox-generation-attempt-6c473f39.txt).
The private ops object now has a shorter name so the call fits on one line; no
generated behavior changes.

Generation from `be07b88fc45d` made patches `0316` and `0317` fully
strict-clean and reached patch `0318`'s first style pass. The test patch had
zero errors, one warning, and two checks: Kconfig requested one more help line
and two fake-ops calls were wrapped. The bounded receipt is in
[`results/buildbox-generation-attempt-be07b88f.txt`](results/buildbox-generation-attempt-be07b88f.txt).
The help now names the covered fault classes and the shorter test-only ops name
keeps both calls on one line; test semantics are unchanged.

Generation from exact clean commit `7aa57a690f9c` passed the managed-source and
six pinned-file checks, semantic source validation, exact three-patch inventory,
replay, and strict checkpatch for every patch with zero findings. The validated
identities are recorded in
[`results/buildbox-generation-7aa57a69.txt`](results/buildbox-generation-7aa57a69.txt)
and [`contract.json`](contract.json). Those exact bytes are canonical patches
`0316`--`0318`.

No device kernel, boot image, partition, firmware service, or hardware
semaphore has been used by this experiment.

## Question

Can the two already-disabled MT6797 protected-state transports meet the exact
named-firmware contracts before they are composed under the transition owner?

The clock transport must perform exactly one 200 ns settle after successful
Linux-port semaphore acquisition and before its first MCUMIXED read. It must
publish only after successful release. The BigiDVFS transport must take two
complete fixed four-word samples through read-only FID `0xc200035f`, publish
only an exact match, and treat instability as retryable. Every failure with a
valid caller record must leave that record all-zero.

## Provenance

- Repository parent: `74f27f7db8618c3564ad780e092e543571b43926`.
- Canonical predecessor: patch `0315`.
- Managed prepared source state:
  `905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e`.
- Exact edited-source identities are pinned in
  [`contract.json`](contract.json).
- Generation and compilation run only on Buildbox from a clean pushed commit.
  No native VM build is permitted.

The prerequisite named-firmware and arbitration decision is recorded by the
[`protected-readback firmware audit`](../2026-08-21-mainline-protected-readback-firmware-audit/README.md).

## Scope

Three logical patches are generated:

1. `0316` repairs the protected-clock
   acquire/settle/read/release/publication order;
2. `0317` makes BigiDVFS take two exact fixed read-only samples; and
3. `0318` adds a focused in-memory KUnit suite for ordering, timeouts, all
   eight secure read fault ordinals, and instability.

The test seam exposes only transport callbacks inside the MediaTek SoC driver
directory. The production clock callback retains the exact existing CSPM
internal-clock and semaphore writes; it adds no PLL, divider, regulator, or
SRAM-LDO write. The BigiDVFS callback retains only the confirmed read FID and
adds no secure write.

## Decision rule

Patch generation passes only if exact source hashes, deterministic editing,
source validation, replay, and strict checkpatch all pass. Compilation then
uses the isolated `protected-readback-kunit` profile. A focused no-network QEMU
run must report all six cases passing before a read-only device candidate can
be considered.

No result here opens the protected-state owner or CPU8/CPU9 admission.
