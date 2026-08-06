# MT6797 hybrid PCM residency and start contract

This is a source-only design boundary for the historical hybrid DVFSP PCM.
It does not copy the firmware array, load a blob, touch hardware, or authorize
the DA921x provider. It defines the minimum evidence a future firmware owner
must provide before the `SEMA_I2C_DRV` callback in patch `0175` can be
registered.

## Required owner inputs

The owner must identify the exact PCM image and target revision, provide a
redistributable or otherwise access-controlled source/license basis, and
record a cryptographic identity for the image. A version string alone is not
enough. The owner must also identify the loader domain and its lifetime: Linux,
secure firmware, or a separately controlled service.

## Public reference-owner evidence

The public Gemian 3.18 source now supplies a positive historical reference for
the owner shape. At commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`,
`mt_cpufreq_hybrid.c` maps CSPM `0x11015000 + 0x1000` and CSRAM
`0x0012a000 + 0x3000` in one probe, obtains the `INFRA_I2C_APPM` clock, and
initializes the SW/HW status windows. Its `cspm_go_to_dvfs()` performs the
reset, image fetch, register/event/wakeup setup, CSRAM record initialization,
and PCM kick. The same source routes `SEMA_I2C_DRV` to the three-word
SW_PAUSE/FW_DONE pause and paired release path. The exact source hashes and
line anchors are in
[`results/public-hybrid-owner-source-20260806.txt`](results/public-hybrid-owner-source-20260806.txt).

The repository `COPYING`/`LICENSE` and the firmware header provide a GPLv2
license basis for the public reference image; source attribution and the GPL
notice must travel with any future derived implementation. The non-governor
descriptor `pcm_dvfs_v0.1_160131_02` (2025 words) matches the retained vendor
ELF string and the public array identity, but mainline packaging has not yet
been admitted. Its `BUG()` and unbounded wait failure behavior is also not
acceptable for a mainline owner. The adapter must use bounded, sticky-fault
failure paths and explicit suspend/resume/clock rollback before it can register
the callback in patch `0175`.

## Required resources and order

The owner must prove all of the following in one attributable start path:

1. The image is resident in memory with a stable physical address and length;
   cache maintenance, alignment, and lifetime are explicit.
2. CSPM `0x11015000 + 0x1000` and CSRAM `0x0012a000 + 0x3000` are mapped by
   the same owner, with no overlapping Linux or secure owner.
3. The I2C_APPM clock reference and any EMI/semaphore ownership are acquired
   before the PCM is touched and have paired, failure-visible release paths.
4. PCM reset and register initialization complete before instruction-memory
   setup.
5. The image base and word length are programmed, the instruction-memory kick
   is issued, and the owner observes the hardware image-ready state within a
   bounded timeout.
6. PCM registers, event and wakeup vectors, per-cluster control words, CSRAM
   log/record pointers, and initial OPP/frequency/voltage/SRAM state are
   initialized before PCM run is requested.
7. PCM run is acknowledged as active and its generation is bound to the Linux
   transfer lease. Only then may the owner implement `SEMA_I2C_DRV` acquire.

The historical public audit identifies this order as reset/init,
`IM_PTR`/`IM_LEN`, `IM_KICK`, `FSM_IM_READY`, register/event/wakeup setup,
`PCM_KICK`, and CSRAM record initialization. Those names describe the contract
boundary; they do not grant permission to reproduce proprietary code or values.

## Runtime lease requirements

After start, the owner must satisfy the existing callback contract without
direct Linux MMIO:

- acquire asserts all three SW_PAUSE bit-13 words and returns all three
  FW_DONE bit-15 acknowledgements within 2 ms;
- the returned owner handle is generation-bound and remains valid for one
  physical I2C6 transaction;
- release clears the pause source and all asserted pause words, or faults
  sticky without guessing an inverse; and
- suspend, resume, clock loss, PCM fault, and owner removal invalidate the
  generation and prevent a stale callback from touching hardware.

## Fail-closed boundary

The following are explicitly insufficient and must return `-EOPNOTSUPP`:

- a CSPM-only mapping with no CSRAM or image-residency proof;
- a `firmware-name` property or `request_firmware()` call without the complete
  start/resource/owner contract;
- a stopped-state observer or Linux generation/cookie lease alone; and
- direct SW_PAUSE/FW_DONE writes while PCM start and ownership are unproven.

Exit requires an attributable owner, exact image identity, complete start
ordering, bounded start acknowledgement, runtime lease responses, and
independent fault/resume evidence. Until then the provider remains read-only
and CPU8/CPU9 remain disconnected.
