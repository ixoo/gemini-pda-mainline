# Candidate Orion results

Orion was installed on logical `boot2` with an exact full-partition readback
and booted successfully. Its console and USB shell were serviceable, but I2C6
failed to bind with `-EINVAL` after the DVFSP handoff became ready, so the
diagnostic file was never created and no I2C transfer ran. The exact,
source-attributable path-check failure is recorded below.

Durable offline evidence:

- `build-reproducibility.txt`: the complete two-build by two-baseline matrix;
- `dtb-lineage-validation.txt`: exact dual-lineage and mutation-test result;
- `installer-validation.txt`: final source-derived guarded-installer result.

Durable device-installation evidence:

- `install-candidate-orion-boot2-20260727.txt`: live-GPT target resolution,
  pre-write safety gates, preserved Hubble backup, bounded Orion write, flush,
  exact full readback, and post-install power-off.

Durable runtime evidence:

- `runtime-candidate-orion-attempt-1-20260727.txt`: successful Orion boot,
  delayed handoff completion, I2C6 probe `-EINVAL`, proof that the one-shot
  trigger was not reached, and the exact source-level node-path mismatch.

## Reproducible build

Two independent clean Orion packages, each paired with both independent
Cassini baseline packages, assembled the same artifact
`candidate-Orion-mt6797-i2c6-6724eb7b` with:

- raw boot-image SHA-256
  `6724eb7bccc5179955681a156468af53ec60557242b50e555cb50a02769a04db`;
- zero-padded 16 MiB SHA-256
  `74f9d9c8cae1213665db2100dda72e0531e0b221cd74a660fc183edcd7bb50d4`;
- complete `SHA256SUMS` SHA-256
  `d72975f4953bfeeff8b9a7da7c1afa931630838ef5c1773c50ba1efe0f7d51e0`.

All four final artifact directories are byte-identical and their strict
manifests pass. `build-reproducibility.txt` records the sanitized input and
output identities.

## Dual DT lineage proof

Orion intentionally carries two independently checked DT ancestries:

- compiled lineage: exact normalized Cassini package provenance SHA-256
  `219f3e15ac0df1277d6de4cb3e97ebc605afdb2da9b3170ab4b7888eab0dead4`,
  compiled Cassini baseline DT SHA-256
  `bf17ba0461512f8d638a79ca1705582e375314445cc1698ac11242dbc6122657`,
  and compiled Orion build-A DT SHA-256
  `0a2aa671dd17e9daf5ce5e3de3d92917129ce639a0a02e0a5041ecf3e3441168`;
- boot lineage: exact hardware-passed Hubble boot DT SHA-256
  `8faee2918ce72b08907affa73bfbaf1c5bbbffafde0f4f4c2693977468291768`
  and derived Orion boot DT SHA-256
  `e189b4741806432af456a2f9a4aa7e250f3e629dcad41726bf221bf2611ccae7`.

Parsed-tree validation proves that each lineage changes only
`/i2c@1100e000:compatible` from its respective baseline. Cross-lineage exact
parsed-property comparison and phandle resolution prove the Orion trees have
the same enabled, childless I2C6 register windows, DVFSP handoff access
controller, main/DMA clocks, interrupt provider/specifier, clock divider, and
bus-cell contract. This separately establishes the source-patch result and the
DT actually serialized into the boot image; it is not a hardware result.

## Evidence required before a boot

The build record must identify and validate:

- the exact Linux `7.1.3` upstream pin, named Orion profile, configuration
  hash, and complete `patches/series-orion-i2c6-idvfs-fifo` inventory;
- two independent byte-identical kernel packages;
- the exact Hubble source artifact and its raw, padded, complete-manifest, DT,
  and initramfs hashes recorded in the parent experiment;
- an exact compiled-source DT lineage from the normalized Cassini package and
  a separate Hubble-derived boot-DT lineage, each changing only the dedicated
  compatible on `/i2c@1100e000`, with identical resolved I2C6 access, clock,
  IRQ, and register resources across the two Orion trees;
- the childless I2C6 node, disabled i2c-dev, disabled DA9214 provider, disabled
  active A72 support, and unchanged ordinary MT6797/I2C5 behavior;
- two independently serialized, byte-identical Android-v0 images and their
  exact raw and zero-padded 16 MiB SHA-256 values;
- successful static, mutation, package, DT-delta, image-layout, and transcript
  validator tests.

A build log is not a hardware result.

## Evidence required from the one-shot run

The sanitized runtime record must contain:

- exact kernel, command line, DT, boot ID, CPU set, handoff, console, keyboard,
  USB-service, childless-I2C6, and zero-pre-counter attribution;
- the initial `state=ready one_shot=unused` status;
- exactly one accepted `run\n` command and final
  `state=done one_shot=consumed` status;
- the attempted/completed count and stop-first error, if any;
- adapter retry telemetry proving configured/during/restored values `1,0,1`,
  so every sample represents exactly one physical transfer attempt;
- every completed or attempted sample in fixed
  `packed-fifo`, `packed-dma`, `aux-dma` mode order and
  `05,06,47` register order;
- each prefill, returned value, transfer return, control, transaction length,
  main and auxiliary transfer length, FIFO count, controller IRQ, and bounded
  APDMA pre/IRQ/post registers;
- an exact completion indication for each accepted transfer, with no
  arbitration-loss, ACK/NACK, missing-completion, or extra-completion status;
- post-run I2C6 counters, kernel warnings, boot ID, CPU set, handoff, and
  serviceability state.

For every packed-FIFO sample, also require controller `DMA_EN` clear, I2C6
APDMA-channel `EN` pre/IRQ/post zero, and no DMA-start counter advance across
the three-sample mode. The shared AP_DMA clock remains intentionally
available for the existing I2C5/bulk-clock contract and is not an acceptance
gate.

Do not include DMA addresses, serial numbers, IMEI values, credentials, or
other personal identifiers. Keep any unsanitized raw capture below the
Git-ignored, mode-0700 artifact tree with mode `0600`.

## Acceptance boundary

The transcript validator may accept a non-live tuple or a stop-first transport
failure as a valid experimental observation. It must reject an apparent
success that also reports arbitration loss, ACK/NACK, or a missing/extra
completion indication; `ret=2` and a changed receive byte are insufficient.
It must not relabel pointer bytes, prefills, zeros, or other values as DA9214
register contents. It must also reject retry telemetry other than `1,0,1`,
any duplicate IRQ count, a FIFO sample with controller DMA enabled, a started
I2C6 APDMA channel, or a FIFO-mode DMA-start counter delta.

Because packed FIFO runs first, a later packed- or auxiliary-DMA failure does
not invalidate or erase its completed FIFO evidence. If packed FIFO itself
fails, preserve its raw failing sample and any completed prefix, stop, and do
not retry an identical candidate.

No Orion evidence may be used to claim a DA9214 provider, regulator operation,
safe register write, CPU8/9 enablement, or general I2C6 support beyond the
exact fixed one-byte combined-read contract.
