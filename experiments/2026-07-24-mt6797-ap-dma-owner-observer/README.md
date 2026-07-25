# Candidate AQ: AP_DMA clock ownership observer

| Field | Value |
|---|---|
| Date | 2026-07-24 |
| Candidate | AQ |
| Status | observer pass on inactive logical `boot2`; AP_DMA owner/refcount pattern captured |
| Profile | `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-ap-dma-observer` |
| Device | current named Gemini PDA development unit |

## Hypothesis and decision gate

Candidate AP showed AP_DMA valid and physically ungated before I2C6 was
probed. The exact AP DT also gives the same AP_DMA clock to enabled UART0 and
I2C5. AQ keeps the successful AO DT unchanged (I2C6 disabled and childless)
and enables only `CONFIG_DEBUG_FS`. Its initramfs mounts debugfs read-only and
saves `/run/clk-summary-early` immediately, then a second snapshot after five
seconds of the inherited console/USB services. The full summaries can be read
through the direct development shell; selected AP_DMA/I2C_APPM/UART0/I2C5/I2C6
rows are mirrored to the console/pstore marker stream.

This is an observation-only test. It does not probe I2C6, access DA9214,
change clocks, request A72 CPUs, write storage, or reboot automatically.

| Observation after manually selecting `boot2` | Decision |
|---|---|
| Both summaries are readable and identify the AP_DMA reference/owner pattern without changing the AO handoff or inherited console/keyboard/USB/reboot contracts | Use the owner evidence to design the next separately scoped I2C6 experiment |
| Debugfs is unavailable or summaries are incomplete | Improve the independent observation path; do not repeat AQ unchanged |
| Any console, keyboard, USB, CPU, spontaneous-reboot, or power regression | Recover through Gemian and treat AQ as failed |

## Runtime result

AQ passed its observation gate on 2026-07-25 after manual `boot2` selection.
The owner reported a readable console. The direct USB shell then confirmed
the inherited console, keyboard-map, USB, and eight-A53 path without requesting
I2C6, touching storage, changing a clock, requesting an A72, or rebooting.
Debugfs was mounted read-only and both the early and five-second `clk_summary`
captures were complete and byte-identical. The direct CCF rows were:

- `infra_ap_dma`: refcount `2`, enable count `2`, enabled `Y`, owner
  `1101c000.i2c` (`dma`);
- `infra_i2c_appm`: refcount `0`, enable count `0`, enabled `N`, owner
  `11015000.dvfsp-handoff` (`i2c`);
- `infra_i2c5`: refcount `1`, enabled `Y`;
- `infra_uart0`: refcount `1`, enabled `Y`.

The early and late summaries were each 35,178 bytes with SHA-256
`6508a7d2a502c9a4b7b8cd0a78d7596f5adb40c676e17fa1dd7a346602c4ec16`.
This identifies the surviving AP_DMA reference as the enabled I2C5 DMA path,
not a transient AQ or I2C6 request. Candidate AQ therefore must not be
repeated unchanged. The next I2C6 experiment must preserve the I2C5/AP_DMA
reference and use a baseline-preserving cleanup oracle for the separate
I2C_APPM handoff gate; DA9214 access, resume, and A72 power remain later gates.

See the complete sanitized capture in
[`runtime-candidate-aq-attempt-1-20260725.txt`](results/runtime-candidate-aq-attempt-1-20260725.txt).

## Build and artifact identity

- Linux 7.1.3, patch series `patches/series-dvfsp-handoff-owner`.
- Kernel package profile is pinned in [`kernel/manifest.json`](../../kernel/manifest.json).
- Exact AO DT: `de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7`.
- `Image.gz`: `428fcc0cd028f3f7854baab2aca3e4927b7fc4c483651f069b124001b2753c02`.
- `System.map`: `8693c3d2c867be57138450a98609c0fd6132aa2ac5dde801c18601c10820e6ee`.
- Kernel config: `550ab140e8748aef36da1f02e56bc774b3296dba3648f9013679caedb31e216b`.
- AQ initramfs: `c3d4b1fb7ef8bd14f0c99de3c89b3997fea78c97cb98bf10490e63d1813f95e1`.
- Raw boot image: `96633efeb1c6197017cb6e03064ecd3a812b37d4c685244513c3930f638b6970` (7,489,536 bytes).
- Exact 16 MiB padded image: `4ad3f29c07a243108f50f3a70049336b116fed80dcb694b2d9e0f872591255c4`.
- Artifact manifest: `3aeca7a2ee5016ae593260efd1d407ecb15053547261e4fe9c34860a3fe99efc`.

The artifact tree is exported under the Git-ignored `artifacts/` path. Its
manifest and all members were checked after export; two independent boot
container assemblies in the recovery VM were byte-identical.

## Installation

The guarded installer resolved logical `boot2` live as `/dev/mmcblk0p30`, with
Gemian root `/dev/mmcblk0p29`, exact size 16 MiB, inactive/unmounted/writable,
and stable full power. It verified the AP predecessor, preserved a private
full backup, wrote only `boot2`, flushed it, and obtained matching remote and
independent local full-partition readbacks:

- predecessor/backup: `602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9`;
- remote and local AQ readback: `4ad3f29c07a243108f50f3a70049336b116fed80dcb694b2d9e0f872591255c4`;
- evidence manifest: `ec6dae5b271974f4c854787a5d12c6015fac1ef90e5c7df0837011ccebb95b7d`;
- reboot/slot selection: none.

The private backup and deployment evidence are in
`artifacts/device-partitions/candidate-aq-boot2-predecessor-20260724T235500Z/`.
