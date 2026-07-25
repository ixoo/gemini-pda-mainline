# Experiment: recover the MT6797 DVFSP/I2C6 arbitration contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-24-mt6797-dvfsp-i2c6-arbitration` |
| Status | `completed` |
| Subsystem | MT6797 DVFSP/CSPM, I2C6, shared I2C_APPM clock |
| Device variant | Gemini PDA, named development unit |
| Date(s) | 2026-07-24 |
| Investigator(s) | Codex and device owner |
| Tracking issue | Candidate AN follow-up |

## Question or hypothesis

Does the exact active Gemian kernel implement a permanent one-way DVFSP
stop/handoff, or does it retain a reversible owner and protect I2C6 with a
per-transaction pause protocol?

The predeclared decision boundary from Candidate AN was:

- if stop is permanent and every restart authority can be excluded, design a
  fail-closed pre-controller handoff;
- otherwise, keep I2C6 disabled until a dedicated coordination provider can
  reproduce the complete per-transfer contract.

## Provenance and environment

- Exact active Android kernel field SHA-256:
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`.
- Exact reconstructed active ELF SHA-256:
  `cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162`.
- Active build string:
  `3.18.41+ #7 SMP PREEMPT Fri Mar 29 10:39:03 GMT 2019`.
- Reconstructed ELF: 64,416 kallsyms-derived symbols; no original build ID,
  relocations, DWARF, or original private source tree.
- Chosen public explanatory source:
  `gemian/gemini-linux-kernel-3.18@59e00a9144d782e148332009a835b99c43382467`.
  The four relevant blobs are identical across checked public revisions from
  2019-03-24 through 2019-04-16. This is not a claim that `59e00a` is the exact
  whole active commit or a reproducible binary-equivalence result.
- Historical board-source corroboration:
  `planet-com/gemini-android-kernel-3.18@c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Exact retained external-firmware pairs:
  LK/LK2 SHA-256
  `75ec9f0ba97af9e68d964b304e0de809f9b4546982570bd16b2e7fe88823282c`,
  TEE1/TEE2 SHA-256
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`,
  and SCP1/SCP2 SHA-256
  `3c65097eeeb4e2d29dd125752cfb648c6da5e3651eabc9dad1da672b2558cd66`.
- Analysis environment: the approved recovery VM through
  `./scripts/dev-vm re-shell`, using GNU `nm`, AArch64 `objdump`, GDB
  multiarch, Git, `sha256sum`, Capstone Python 4.0.2, radare2 5.5.0, and
  immutable private evidence below `~/reverse-engineering/`.

The exact active source revision remains unresolved. The current public
`d388d350...` head changes three of the four relevant source blobs, so its
source is corroboration only; active-binary conclusions use the exact ELF.

## Safety assessment

This investigation was read-only. It did not access the live device, write a
partition, change a clock or register, issue an I2C transaction, load firmware,
or reboot. Private kernel/userspace artifacts remained in Git-ignored,
mode-restricted storage. No firmware, partition image, proprietary source,
credential, device identifier, or disassembly dump is committed here.

## Associated code

- [`scripts/verify-active-contract.sh`](scripts/verify-active-contract.sh)
  checks the exact private ELF identity, pinned public source blobs, required
  active symbols, direct call counts, and outer clock/transfer ordering. It is
  read-only and must be run in the recovery VM. It does not reproduce the
  normalized comparator or external-firmware audit.
- [`results/active-contract-summary-20260724.txt`](results/active-contract-summary-20260724.txt)
  is the sanitized result.
- [`results/external-cspm-writer-audit-20260724.txt`](results/external-cspm-writer-audit-20260724.txt)
  records the bounded exact LK/TEE/SCP writer audit. That result was produced
  by manual analysis of private payloads; no scanner or independently runnable
  reproduction is committed.
- Existing private reconstruction and provenance procedures are recorded in
  the
  [active Gemian kernel reconciliation](../2026-07-22-a72-firmware-power-contract/results/active-gemian-kernel-reconciliation-20260723.txt).

## Procedure

1. Enter the approved recovery VM and verify the exact reconstructed ELF
   checksum.
2. Resolve the DVFSP, cpufreq, and I2C symbols from the exact active ELF.
3. Disassemble only the named functions and trace direct callers of stop,
   restart, kick/resume, pause/release, and I2C transfer.
4. Manually compare address/immediate-normalized instruction shapes with an
   existing private comparator build using the pinned `59e00a` source blobs.
   The
   comparator differed from the active configuration by
   `CONFIG_MTK_A72_TRANSITION_OBSERVER=y`; its complete resolved configuration,
   ELF identity, exact toolchain identity, and normalization implementation
   were not preserved in this record.
5. Reconcile the disassembly against the pinned GPL source, treating source as
   an explanation of exact active machine code rather than as proof by itself.
6. Search the retained Android ramdisk and immutable vendor userspace for the
   writable cpufreq controls and adjacent owner services.
7. Record all timeout, partial-acquire, release, and clock-reference exits.
8. Manually scan the meaningful exact LK, TEE, and SCP payload extents for raw
   little-endian CSPM addresses/keys and direct architecture-specific immediate
   constructors. Classify every positive `0x1101xxxx` reference by surrounding
   loads/stores. Treat computed pointers and SCP-local aliases as residual
   uncertainty rather than as a negative result.

The manual external-firmware audit is not reproducible from this repository:
the private payloads are not committed, and no analysis program was preserved.
The following details pin the scope of the retained result without claiming a
repository scanner. The payload bounds came from each MediaTek header rather
than from partition size or trailing padding: LK `[0x200,0x697f8)`, TEE
`[0x200,0x18000)`, SCP loader `[0x200,0x600)`, and SCP main
`[0x800,0x9a44)`. The constructor pass decoded a candidate instruction at
every architectural alignment: AArch64 step 4 for TEE, ARM step 4 plus Thumb
step 2 for LK, and both conservative ARM/Thumb passes for SCP. It paired direct
`MOVZ/MOVK` or `MOVW/MOVT` high-half `0x1101` constructions with the nearest
straight-line low-half definition of the same register, then classified
following direct loads/stores. Key-value constructors with high half
`0x0b16` were checked separately. This is exhaustive only for those direct
move-immediate forms within the declared payloads; it does not cover
ADR/ADRP arithmetic, tables, arbitrary computed addresses, encrypted code, or
SCP-local address aliases.

Reproduction of the bounded identity/call-graph checks:

```sh
bash experiments/2026-07-24-mt6797-dvfsp-i2c6-arbitration/scripts/verify-active-contract.sh \
  ~/reverse-engineering/work/gemini-kernel-active-20260723/vmlinux.elf \
  ~/src/reference/gemian-linux-kernel-3.18
```

## Observations

### Bounded normalized comparator note

A retained manual comparison reported matching shapes after normalizing
PC-relative data immediates and one spinlock target alias:

| Group | Instructions | Normalized shape SHA-256 |
| --- | ---: | --- |
| permanent stop/restart | 212 / 212 | `5f2b77ef3355c2c5d65a8af14401dd4e7b499520cc8f24061022d46c7ab3abac` |
| `SEMA_I2C_DRV` and I2C transfer | 1,604 / 1,604 | `603473075001fbe458d0e18a796746416403df7fdbf38e38e28ff91a2792560d` |

The comparator was not configuration-identical to the active kernel:
`CONFIG_MTK_A72_TRANSITION_OBSERVER=y` was enabled only in the comparator.
This record pins the active ELF and configuration checksums, public source
blobs, instruction counts, and reported normalized hashes, but not the
comparator ELF/configuration checksums, exact toolchain, or normalization
implementation. The normalized result is therefore supporting manual evidence,
not a reproducible binary-equivalence or whole-tree-provenance claim. The
scripted symbol and direct-call checks below stand independently against the
exact active ELF.

### Stop is reversible

`cpuhvfs_stop_dvfsp_running()` reaches `cspm_stop_pcm_running()` under the
global `dvfs_lock`. The latter:

1. pauses with the `PAUSE_INIT` bit;
2. asserts `SW_PAUSE` for all three physical clusters and waits up to 2 ms for
   all three `FW_DONE` bits;
3. disables one I2C_APPM CCF reference on successful pause;
4. disables TWAM, R7 power I/O, the PCM timer, wake events and internal IRQs;
5. toggles PCM software reset and requires FSM state `0x00048490`;
6. clears the hardware-governor flag.

It does not erase code/IM or CSRAM, clear initialization state, unregister the
provider, unprepare the shared clock, or set an ownership latch. A pause
timeout leaves the three `SW_PAUSE` writes asserted but does not record a
pause-source bit or unwind them.

The active kernel retains three restart routes:

- root/group-writable mode-0664
  `/proc/cpufreq/enable_cpuhvfs`; a later nonzero write calls
  `cpuhvfs_restart_dvfsp_running()`;
- the initial cpufreq probe kick when `enable_cpuhvfs` is nonzero;
- syscore resume, which re-kicks when the outer enable flag is still nonzero.

A normal successful proc stop sets that outer flag to zero, but a later proc
write can restart. The writer also discards the internal switch return value
and reports the byte count. The APIs are built in and not module-exported in
this no-modules active kernel.

### `SEMA_I2C_DRV` is a pause source, not a hardware semaphore

`SEMA_I2C_DRV` is enum user 1. Its get path bypasses every CSPM semaphore
register and calls:

```text
cspm_pause_pcm_running(PAUSE_I2CDRV)
```

Its release path calls the matching unpause. Only `SEMA_FHCTL_DRV` (user 0)
uses `CSPM_SEMA0_M0`. This I2C6 protocol must not be conflated with the
FHCTL/DVFSP hardware semaphores, SCP I2C0/1 arbitration, PERICFG I2C
arbitration, or I2C7 GPUPM ownership.

When no other pause source is held, acquire:

1. takes `dvfs_lock`;
2. sets `SW_PAUSE` bit 13 in `SW_RSV0/1/2` and mirrors CSRAM;
3. delays 10 us;
4. polls `FW_DONE` bit 15 in `SW_RSV3/4/5` every 10 us for at most 2 ms;
5. disables DVFSP's prepared I2C_APPM clock reference;
6. records pause-source bit `0x2`.

Release clears bit `0x2`. Only when the whole pause map reaches zero does it
enable DVFSP's I2C_APPM reference, clear `SW_PAUSE` for enabled clusters,
mirror state, record time, and wake DVFS waiters. Clock-enable failure or no
enabled cluster is fatal in the vendor implementation.

`pause_src_map` starts with `PAUSE_INIT`. Firmware kick leaves that bit set
until the first cluster-on callback calls the common unpause helper. Normal
running state therefore owns one persistent DVFSP enable reference to
I2C_APPM. After stop, `PAUSE_INIT` remains held and the successful stop has
removed that persistent reference.

### Exact I2C6 coverage and ordering

I2C6 alone is marked `mediatek,appm_used`. It uses controller
`0x1100e000`, DMA `0x11000500`, SPI 88, and the same
`INFRA_I2C_APPM` gate as DVFSP. It has neither the GPU-PM nor buffered/hardware
trigger property.

The exact outer transfer order is:

```text
enable DMA/main clocks
  -> lock controller mutex
    -> prepare one physical transaction
      -> acquire DVFSP pause
        -> program I2C/DMA/IRQ, START, wait, reset/drain as needed
      -> release DVFSP pause
    -> inspect/copy the result
  -> unlock controller mutex
-> disable controller clocks
```

Clock ordering is essential. The controller first takes its own reference to
the shared I2C_APPM gate; pausing then drops DVFSP's reference while keeping
the physical clock available to the controller transaction. Release restores
DVFSP's persistent reference before the outer wrapper drops the transaction
reference. Linux 3.18 CCF enable counts are shared per clock core, so the
physical gate changes only when the combined count crosses zero.

The active binary has exactly two get call sites—the second is the immediate
retry—and one release call site in `__mt_i2c_transfer`. Every successful
acquire reaches release after success, speed failure, transfer timeout, or
ACK/NACK error. Combined write/read and grouped writes each hold one pause
across one physical transaction. DMA read copy-back occurs after release.

### Failure and unwind behavior

| Exit | Acquire/release behavior |
| --- | --- |
| outer clock failure | no acquire; unwind applicable I2C6 clocks |
| invalid message or preparation failure | no acquire |
| first pause timeout | log nominal 2 ms and retry without repairing partially asserted `SW_PAUSE` |
| second pause timeout | log nominal 4 ms, dump state, unconditional vendor `BUG_ON(1)`; no transfer or release |
| transfer success/error after acquire | always release before propagation |
| unpause clock-enable failure or no enabled cluster | fatal vendor path; no recoverable return |

The I2C core does not retry these returned errors. The vendor path is
sleepable and is not safe for atomic I2C APIs.

### Remaining provenance and ownership gaps

- The exact private whole source tree and original ELF metadata are absent.
- The retained Android/vendor userspace contains no direct
  `enable_cpuhvfs` writer, but it is not the complete post-pivot Gemian root
  filesystem.
- EEM and frequency-hopping code write CSPM clock/semaphore resources, though
  source and active call analysis found no second PCM kick implementation in
  the kernel.
- A72 iDVFS is a third user of the same CCF clock core: first-A72 enable adds
  an I2C_APPM reference before DA9214 access, and last-A72 disable drops it.
  Future mainline A72/iDVFS work must therefore coexist with the same shared
  counter; it is not part of ordinary I2C6/DVFSP arbitration.
- Public source and the active normal-world kernel cannot exclude a secure
  firmware, LK, or SCP writer solely by source inspection.
- No runtime trace proves timing of an actual Gemian I2C6 pause/restart.

### Exact retained external-firmware audit

The redundant LK, TEE, and SCP partition pairs are byte-identical within each
pair. A raw little-endian scan found no occurrence of CSPM `0x11015000`,
PCM control `0x11015018`, or the relevant keyed control values. That raw result
alone is not evidence of absence because code can construct addresses from
immediates.

A direct-immediate constructor scan over each meaningful architecture-specific
payload produced these bounded results:

| Owner | Observation |
| --- | --- |
| TEE/ATF | Constructs `0x11015000`, writes keyed `0x0b160001` to `+0`, and uses secure semaphore `+0x448` in MP2/B-cluster power/clock helpers. No direct construction/access to `+0x18` and no PCM kick/reset constant was found. |
| LK | No direct CSPM `+0`, `+0x18`, or semaphore constructor. It constructs watchdog-latch registers `+0x190/+0x194/+0x198` and only loads them for diagnostics. |
| SCP | No direct physical CSPM address/key constructor in its loader or main payload. A CM4-local peripheral alias or computed pointer remains unexcluded. |

This finds no positive external PCM restart writer in the exact retained
payloads. It does prove that ATF remains an interfering CSPM
register-clock/semaphore owner, so a Linux handoff must detect unexpected
state and cannot claim the whole block is normal-world-exclusive. The negative
result is limited to direct constructors and classified references; it does
not prove the absence of computed addresses.

## Analysis

Candidate AN's stable reset-like snapshots are consistent with a stopped PCM,
but the ungated shared clock and absence of a permanent latch remain material.
Calling the vendor stop API once would not turn that observation into a
race-free ownership handoff: the stop is designed to be reversed, drops only
one clock reference, and leaves restart authorities.

The active vendor design can be used as a behavioral specification, but its
failure policy must not be copied. A mainline coordination provider would need
to own the complete pause state machine, pause-source map, lock, CSRAM mirrors,
firmware protocol, and shared-clock lifetime. The I2C controller would acquire
after its clocks are enabled but before any transaction programming and
release on every acquired exit. A timeout must fault closed without issuing a
transaction; because the vendor timeout can leave partial `SW_PAUSE` writes,
blind unpause is not a safe unwind.

The exact external audit found no direct PCM restart writer, while retaining
ATF interference and SCP-alias uncertainty. That is sufficient to design a
sticky, one-way mainline handoff owner, but not to trust an unverified clock
toggle or cached snapshot. The owner must complete before I2C6 can probe,
normalize the stopped-state clock lifetime through CCF, revalidate the PCM and
gate after the transition, remain faulted after any mismatch, and revalidate
on resume. It must not expose a restart API or synthesize the persistent clock
reference used only by running DVFSP.

## Conclusion

`confirmed` for the exact active Gemian control-flow paths checked directly;
the pinned public blobs explain those paths, while the unrepeatable normalized
comparator remains supporting evidence only:

- DVFSP stop is a reversible PCM reset, not a permanent handoff.
- I2C6 protection is a per-physical-transaction pause-source protocol, not a
  hardware semaphore acquisition.
- Candidate AN does not authorize I2C6 access.

`inconclusive` for a permanent current-boot mainline handoff until the proposed
one-way owner itself is reviewed and tested. The exact retained payloads
contain no positive direct external PCM restart writer; ATF interference and
an SCP-local alias remain explicit residual risks.

## Follow-up

1. Complete the fail-closed, one-way handoff-owner design review: probe order,
   CCF normalization, sticky fault state, resume revalidation, and an explicit
   I2C6 dependency.
2. Preserve the normal-running persistent DVFSP reference and separate A72
   iDVFS reference as design facts. A handoff-only owner must model
   stopped/`PAUSE_INIT` state and must not synthesize either reference.
3. Keep I2C6 and DA9214 disabled in the first handoff-owner candidate. Its
   unique result must be a verified ungated-to-gated CCF transition plus
   stable stopped PCM state and later revalidation, not marker text.
4. Only after that candidate establishes the invariant should a separate
   resource-only legacy DA9214 identification candidate be reviewed.
