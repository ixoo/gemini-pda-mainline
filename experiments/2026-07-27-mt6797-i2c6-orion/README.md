# Experiment: Orion — MT6797 I2C6 packed-length FIFO discriminator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-27-mt6797-i2c6-orion` |
| Status | `booted and serviceable; I2C6 probe failed before any transfer due exact node-identity bug` |
| Subsystem | MT6797 I2C6/iDVFS combined write-read receive path |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-27 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Does the named Gemini's dedicated I2C6/iDVFS controller require the recovered
MT6797 contract—packed WRRD lengths in `TRANSFER_LEN` and FIFO/PIO for
one-byte legs—to return real receive bytes, instead of the pointer-correlated
or unchanged-buffer results produced by the current auxiliary-length/APDMA
path?

Orion changes only that controller contract. For a combined one-byte pointer
write and one-byte read, the special I2C6 path programs packed length
`0x0101` (`tx[7:0] | rx[12:8]`) and can use the eight-byte controller FIFO.
Ordinary MT6797 controllers, including the I2C5 keyboard controller, retain
their existing compatible and auxiliary receive-length behavior.

A root-only one-shot diagnostic reads fixed address `0x69` and fixed register
pointers `0x05`, `0x06`, and `0x47` in this exact order:

1. packed-length FIFO;
2. packed-length APDMA;
3. auxiliary-length APDMA.

The receive buffers begin as `a5,5a,3c`. The previously observed live Gemian
tuple is `d9,d0,c0`, but Orion does not assume that tuple proves a chip
identity. It records raw bytes and programmed controller/APDMA state so the
three transport contracts can be compared within one boot.

The fixed order is causal. FIFO runs first because it keeps the I2C6 APDMA
channel unstarted for the first decisive observation: controller `DMA_EN` is
clear, the channel's APDMA `EN` snapshots remain zero, and the DMA-start
counter does not advance. The shared AP_DMA clock remains intentionally
available because I2C5 and the bulk-clock contract still need it; Orion does
not use clock-off as evidence. The diagnostic calls `mtk_i2c_init_hw()` before
the first transfer of every mode, resetting both the I2C controller and its
APDMA block so a later mode does not inherit the preceding mode's programming.
It stops at the first transfer result other than exactly two messages. Because
FIFO is first, a later DMA error cannot erase its completed samples; a FIFO
error still preserves the raw failing sample and any completed FIFO prefix as
the decisive result.

## Prior evidence

Observation and inference remain separate:

- Hubble restored the complete byte-and-mode-exact, hardware-passed Cassini
  serviceability boundary: delayed readable console, keyboard, USB gadget
  Ethernet, eight online CPUs, and native reboot.
- Photon r2 issued six combined WRRD requests on exact Hubble. Every ioctl
  returned success and all controller counters advanced, but each CPU-visible
  receive byte stayed equal to its distinct prefill. This rejected Cassini's
  zero-initialized results as register values.
- Voyager's valid STOP-separated one-message reads returned the immediately
  preceding pointer bytes, `06,47`.
- Mariner changed from direct DMA-safe `I2C_RDWR` buffers to the ordinary
  i2c-dev/core zeroed bounce-buffer path. It still returned exact pointer echo
  `06,47`, with all four counters advancing `14->18`. The fault therefore
  survives both userspace buffer APIs and lies below that boundary.
- Recovered vendor source and the matching working Gemian 3.18 binary agree
  that this dedicated I2C6/iDVFS instance packs WRRD transmit and receive
  lengths in `TRANSFER_LEN` and uses the eight-byte controller FIFO when each
  leg is at most eight bytes. Ordinary MT6797 controllers use the auxiliary
  receive-length register.

The last item is implementation evidence for the Orion hypothesis, not
mainline hardware proof. Only an exact Orion runtime result can establish the
behavior of the new path on the named unit.

## Provenance and environment

- Kernel release and upstream input: Linux `7.1.3`, pinned by
  `kernel/manifest.json`.
- Named profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-orion`.
- Patch series: `patches/series-orion-i2c6-idvfs-fifo`.
- Orion configuration policy: `configs/gemini-i2c6-orion.fragment`.
- Orion logical changes:
  `patches/v7.1.3/0114-dt-bindings-i2c-mediatek-add-MT6797-iDVFS-controller.patch`,
  `0115-i2c-mediatek-support-MT6797-iDVFS-transfer-format.patch`,
  `0116-arm64-dts-mediatek-identify-Gemini-I2C6-iDVFS-block.patch`, and
  `0117-i2c-mediatek-add-fixed-Orion-I2C6-diagnostic.patch`.
- Orion deliberately proves two distinct DT lineages rather than assuming the
  package's compiled DT is the DT serialized into the boot image:

  - The compiled-source lineage starts from the exact pre-Orion Cassini kernel
    package. Its normalized build provenance has SHA-256
    `219f3e15ac0df1277d6de4cb3e97ebc605afdb2da9b3170ab4b7888eab0dead4`
    and its compiled `mt6797-gemini-pda.dtb` has SHA-256
    `bf17ba0461512f8d638a79ca1705582e375314445cc1698ac11242dbc6122657`.
    Build A's compiled Orion DT has SHA-256
    `0a2aa671dd17e9daf5ce5e3de3d92917129ce639a0a02e0a5041ecf3e3441168`.
    Parsed-tree comparison proves that its only Cassini DT change is
    `/i2c@1100e000:compatible`.
  - The boot-serviceability lineage starts independently from Hubble's exact
    hardware-passed boot DT, SHA-256
    `8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768`.
    The derived Orion boot DT serialized into build A has SHA-256
    `e189b4741806432af456a2f9a4aa7e250f3e629dcad41726bf221bf2611ccae7`.
    Its only parsed-tree change from Hubble is the same I2C6 compatible.

  The two Orion DTs need not have identical global bytes or phandle numbers:
  they serve different provenance purposes. Exact parsed-property comparison
  and phandle resolution nevertheless prove an identical enabled, childless
  I2C6 contract:
  controller/APDMA resources `0x1100e000/0x1000` and
  `0x11000500/0x80`; access controller
  `/dvfsp-handoff@11015000`; `main` and `dma` clocks from
  `/syscon@10001000` with IDs `0x36` and `0x2e`; interrupt provider
  `/interrupt-controller@10200620` with specifier `0,0x58,8`; and unchanged
  clock divider, address cells, size cells, and status.
- Exact Hubble source artifact:
  `candidate-Hubble-cassini-rollback-e02e2673`.
- Exact Hubble raw Android-v0 member:
  `gemini-mt6797-da9214-cassini.boot.img`, size 7,645,184 bytes, SHA-256
  `e02e2673ca054d3e4081f5234d26a394617777e8496417fd75196a948d55fa4d`.
- Exact Hubble 16 MiB padded image SHA-256:
  `febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1`.
- Complete Hubble/Cassini `SHA256SUMS` SHA-256:
  `0d1a954827f5ebd31abc12b4d0a207105c5e270403a9b3a66cbd70626e5b2306`.
- Exact Hubble DT member:
  `mt6797-gemini-pda-da9214-cassini.dtb`, SHA-256
  `8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768`.
  Orion's candidate DT may differ from it only at the I2C6 compatible
  property.
- Exact retained Hubble initramfs member:
  `gemini-da9214-cassini-initramfs.img`, SHA-256
  `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f`.
  Its Cassini helper is inert for I2C access because Orion disables
  `CONFIG_I2C_CHARDEV`.
- Build environment: the repository recovery VM through
  `./scripts/dev-vm build-kernel`.
- Intended boot path: owner-selected logical `boot2`, only after a separate
  guarded installation. No partition access, installation, shutdown, reboot,
  or device connection is part of preparing this experiment.

Two independent clean builds and both independent Cassini baselines produced
the same final artifact
`candidate-Orion-mt6797-i2c6-6724eb7b`: raw SHA-256
`6724eb7bccc5179955681a156468af53ec60557242b50e555cb50a02769a04db`,
zero-padded 16 MiB SHA-256
`74f9d9c8cae1213665db2100dda72e0531e0b221cd74a660fc183edcd7bb50d4`,
and `SHA256SUMS` SHA-256
`d72975f4953bfeeff8b9a7da7c1afa931630838ef5c1773c50ba1efe0f7d51e0`.
All four final package/baseline pairings are byte-identical. A compile result
alone does not establish hardware behavior.

## Runtime outcome

The exact, full-readback-verified Orion image booted on the named unit with
CPUs 0-7 and its USB development shell available. I2C6 correctly deferred
until the 45-second DVFSP handoff reached `ready`; both consumer clock checks
then passed, but the I2C driver returned `-EINVAL` and removed its adapter.
Consequently the diagnostic debugfs file never existed, the invocation guard
remained absent, and no transfer ran.

Exact-source tracing found a deterministic software identity-check bug:
`mtk_i2c_orion_init()` compared `of_node_full_name()` with the absolute path
`/i2c@1100e000`, while pinned Linux 7.1.3 stores this FDT node's `full_name` as
the bare node name `i2c@1100e000`. The next candidate must resolve the absolute
path with `of_find_node_by_path()`, compare node pointers, and release the
reference. This result establishes neither FIFO nor DMA behavior. See
`results/runtime-candidate-orion-attempt-1-20260727.txt`.

## Safety assessment

The kernel exposes the diagnostic only on the exact
`mediatek,mt6797-idvfs-i2c` instance at `/i2c@1100e000`, after the DVFSP
handoff is ready and only while the adapter has no child device and no prior
transfer counters. Its debugfs file is mode `0600`, accepts exactly `run\n`,
and consumes its one-shot state before attempting a transfer. There is no
argument-controlled address, register, mode, length, retry, or scan.

While holding the root-adapter lock, run-all records the adapter's configured
retry count, sets it to zero for the fixed sequence, and restores the original
value on every transfer exit. The status records before/during/after values;
Orion requires `1,0,1`. Thus an arbitration loss cannot make
`__i2c_transfer()` issue an unrecorded second physical transfer.

The experiment is not literally bus-read-only: every observation sends one
fixed register-pointer byte before reading one byte. It never sends a register
data byte. The only address is `0x69`, the only pointers are
`0x05,0x06,0x47`, and the maximum complete run is nine combined transfers.
It stops on the first transport error.

`mtk_i2c_init_hw()` deliberately resets the controller and APDMA block before
each mode. This is a bounded volatile hardware-state mutation and is part of
the attribution contract. Orion has no persistent-storage, partition,
watchdog, reboot, shutdown, slot-selection, raw-memory, page-control,
regulator-control, or CPU-control operation.

I2C6 remains childless. `CONFIG_I2C_CHARDEV`, the DA9214 regulator provider,
and active MT6797 A72 power support are disabled. CPUs 8 and 9 remain
unrequested. The ordinary I2C5 keyboard path is unchanged. Thus the candidate
cannot use an arbitrary userspace I2C interface or turn a diagnostic read into
a DA9214 or A72 enablement attempt.

Any boot-attribution mismatch, serviceability regression, nonzero pre-run
I2C6 counter, unexpected child, handoff failure, transfer error, arbitration
loss, ACK/NACK error, missing or extra completion indication, controller
timeout, FIFO-count mismatch, kernel warning, or automatic reboot is a stop
condition. A changed receive byte or transfer return of two cannot override
an interrupt-status failure. Preserve the first evidence and do not repeat an
identical image.

## Associated code

- The four Orion patches and named series listed above implement the binding,
  special controller data, Gemini I2C6 compatible, and fixed diagnostic.
- `configs/gemini-i2c6-orion.fragment` fixes the local version, diagnostic,
  debugfs, serviceability command line, and disabled i2c-dev/provider/A72
  boundary.
- `kernel/manifest.json` pins the named build profile.
- Scripts beside this record build and validate the package, exact DT delta,
  Android-v0 candidate, static contracts, and future result transcript.
- Hubble's existing exact-artifact validator remains the source-boundary
  authority for the retained DT/initramfs and serviceability members.

Build and offline validation require no hardware access. A future runtime
capture uses only the direct USB development link after a separately
validated, owner-selected `boot2` boot.

## Procedure

1. Build the named Orion profile twice in independent recovery-VM output
   directories with `./scripts/dev-vm build-kernel`.
2. Require byte-identical kernel packages and validate the exact profile,
   patch inventory, configuration, symbols, local version, and fixed
   diagnostic markers.
3. Prove the compiled-source DT lineage from the exact normalized Cassini
   package: require the compiled Orion tree to differ only at I2C6's dedicated
   compatible.
4. Independently derive the boot DT from the exact Hubble serviceability base.
   Retain Hubble's initramfs byte-for-byte and require this second DT tree to
   differ only at the same I2C6 compatible. Resolve phandles in both Orion
   trees and require identical I2C6 access-controller, clock, interrupt, and
   register resources.
5. Serialize and inspect the Android-v0 image twice, require byte identity,
   pad it with zeros to exactly 16 MiB, and record raw and padded hashes.
6. Run all offline contract and mutation tests. Reject arbitrary addresses,
   registers, input tokens, mode orders, length encodings, or enabled
   i2c-dev/provider/A72 paths.
7. Record the pre-boot hypothesis and candidate hashes in `results/`. A
   separate guarded workflow may then install only inactive logical `boot2`;
   it must perform the repository's full backup and matching full-partition
   readback checks. This experiment itself performs no installation.
8. After the owner selects `boot2`, first establish exact Orion kernel,
   command-line, DT, handoff, childless-I2C6, counter, CPU, console, keyboard,
   and USB-service attribution. Do not invoke the diagnostic if any gate
   fails.
9. Mount debugfs if necessary, read the root-only status once, and require
   `state=ready`, `one_shot=unused`, zero pre-run I2C6 counters, and the
   configured retry value one.
10. Write exactly `run\n` once to the fixed `orion-run-all` file. Capture its
   complete status, I2C6 counters, retry telemetry, relevant kernel log, boot
   ID, CPU set, and serviceability state. Require retries `1,0,1` and do not
   retry on the same boot.
11. Validate the transcript offline, classify it with the decision table, and
    take only the corresponding next action. Reject arbitration loss,
    ACK/NACK, or anything other than the exact expected completion indication,
    regardless of transfer return or receive value.

## Pre-boot hypothesis, evidence, and decisions

| Exact result | Unique attributable evidence | Decision-changing next action |
| --- | --- | --- |
| Packed FIFO completes all three reads as `d9,d0,c0`, with FIFO count one, packed length `0x0101`, controller `DMA_EN` clear, I2C6 APDMA `EN` pre/IRQ/post zero, and no DMA-start counter delta | Keeping the I2C6 APDMA channel unstarted while using the recovered packed-length contract restores the prior live tuple; this says nothing about the intentionally available shared AP_DMA clock | Treat the short FIFO path as the first functional mainline I2C6 read path. Reproduce with a new independent observation before considering any provider; repair or exclude short-transfer APDMA separately. |
| Packed FIFO produces `05,06,47` | Pointer correlation survives removal of APDMA and comes from the controller/FIFO/wire boundary or transaction semantics | Do not change DMA or add a regulator. Audit FIFO ordering, START/control programming, timing, and obtain a physical-bus trace if available. |
| Packed FIFO leaves `a5,5a,3c`, reports an invalid FIFO count, times out, or returns another error | The special packed/FIFO path does not establish receive data; the raw first failure is preserved and later modes intentionally do not run | Stop without retry. Reconcile the exact special-controller reset, clock, FIFO, and interrupt contract against source/binary evidence. |
| Packed FIFO returns stable non-pointer bytes, packed DMA echoes pointers or preserves prefills, and auxiliary DMA is the same or worse | The decisive differential is FIFO versus APDMA, not the userspace/core buffer path | Keep I2C6 short reads on FIFO and localize APDMA direction, address, length, completion, and coherency before allowing longer transfers. |
| Packed FIFO and packed DMA agree while auxiliary DMA differs | The packed WRRD length encoding, rather than DMA itself, is the decisive correction | Retain the dedicated compatible and packed encoding; test DMA length boundaries offline and with one separately designed bounded runtime case. |
| Packed DMA and auxiliary DMA differ, but FIFO has already completed | The preserved FIFO tuple remains primary; the DMA comparison isolates encoding without spending another boot | Use the exact register snapshots to choose between length-programming and APDMA-state fixes. Do not repeat Orion unchanged. |
| A later DMA transfer errors | All completed FIFO samples and the failing DMA sample remain available because FIFO ran first and stop-first is enforced | Use the preserved FIFO result as the hardware conclusion; diagnose only the failed DMA mode in a new artifact if that knowledge is still required. |
| All three modes complete with the same stable non-pointer tuple | Both DMA forms happen to deliver the same bytes in this bounded case; this does not erase the recovered special hardware contract | Retain the correct dedicated compatible/FIFO policy, but do not claim the prior fault was uniquely length encoding or DMA without an additional independent discriminator. |
| Boot/serviceability or pre-run gates fail | The candidate never reaches the exact observation boundary | Preserve console/pstore/USB evidence, return to Hubble, and change only the evidenced failing layer. Do not invoke or repeat the diagnostic. |

No result identifies the device at `0x69`, establishes a safe register-write
contract, enables a regulator, or authorizes CPUs 8/9.

## Observations

Two clean Orion builds were assembled against both independent Cassini
baselines and passed the offline dual-lineage DT proof. The full 2x2 matrix is
byte-identical; its raw, padded, manifest, compiled-DT, and boot-DT hashes are
recorded above and in `results/build-reproducibility.txt`.

No Orion device, partition, or device-network session was accessed while
creating or validating the builds and assembly matrix. No runtime value is
recorded here. Hardware evidence must be added as a separate, sanitized file
under `results/`.

## Analysis

Pending the first exact Orion runtime result.

The experiment is designed to answer more than a simple success/failure
question in one boot. FIFO-first leaves the I2C6 APDMA channel unstarted; the
two following modes hold address, register order, message shape, kernel, and
device state fixed while changing only the packed-versus-auxiliary length and
FIFO-versus-DMA choices. The shared AP_DMA clock remains available in every
mode and is not a discriminator. Per-mode controller/APDMA reset and raw
pre/IRQ/post snapshots limit retained state as an alternative explanation.

This does not provide a wire capture. A successful controller interrupt and a
CPU-visible byte remain indirect evidence of a bus transaction, and agreement
with `d9,d0,c0` remains consistency with prior Gemian observations rather than
proof of silicon identity.

## Conclusion

`Pending hardware result.` Orion's dual DT proof establishes that both the compiled source
lineage and the actually serialized Hubble-derived boot lineage carry the
intended identical I2C6 resource contract with only the compatible changed
from their respective baselines. The 2x2 build/assembly matrix fixes the final
artifact identities. The named Gemini and exact reproducibly selected
candidate must still produce a validated one-shot transcript before the
hardware hypothesis can be confirmed or rejected.

## Follow-up

Do not return to a DA9214 provider or active A72 enablement until Orion
establishes a functional, attributable I2C6 receive path. Do not update the
hardware support matrix from a build result. After the one-shot run, preserve
the complete raw evidence, select exactly one decision branch above, and make
the next candidate change only that evidenced layer.
