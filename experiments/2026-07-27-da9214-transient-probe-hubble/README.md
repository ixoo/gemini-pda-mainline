# Experiment: Hubble — exact Cassini recovery base for a transient probe

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-27-da9214-transient-probe-hubble` |
| Status | `booted; exact volatile Photon r2 observation completed` |
| Subsystem | Boot serviceability control and out-of-band DA9214 observation |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-27 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Will replacing failed Photon r2 with the complete, byte-exact
hardware-passed Cassini artifact restore Cassini's delayed but readable console,
keyboard, USB gadget Ethernet, and native reboot boundary?

Hubble changes no boot-bearing byte. Its artifact is a complete byte-and-mode
clone of exact Cassini; only the enclosing artifact directory is renamed.
This makes the boot a clean recovery control. A future one-shot helper may be
transferred over the already validated USB-only development service after
boot, but that transfer is not embedded in Hubble and cannot change this boot
comparison.

## Provenance and environment

- Exact source artifact:
  `candidate-Cassini-da9214-direct-address-e02e2673`.
- Hubble artifact directory:
  `candidate-Hubble-cassini-rollback-e02e2673`.
- Exact raw Android-v0 member:
  `gemini-mt6797-da9214-cassini.boot.img`.
- Raw SHA-256:
  `e02e2673ca054d3e4081f5234d26a394617777e8496417fd75196a948d55fa4d`.
- Raw size: 7,645,184 bytes.
- Exact 16 MiB padded SHA-256:
  `febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1`.
- Complete Cassini `SHA256SUMS` SHA-256:
  `0d1a954827f5ebd31abc12b4d0a207105c5e270403a9b3a66cbd70626e5b2306`.
- Exact required live predecessor: installed and full-readback-verified
  Photon r2 padded SHA-256
  `0ffe1ee750ff219c9ee6f9d4809ecb8748bdd2a35ba63d68a99b3d74e599c2f7`.
- Build environment: recovery VM; no kernel compilation or container
  serialization occurs because those operations would be an unnecessary path
  for changing hardware-passed Cassini bytes.
- Boot path: owner-selected non-primary logical `boot2` after a separate
  guarded installation.

## Safety assessment

The builder and validator are storage-inert. They accept only an exact complete
Cassini artifact, copy every regular member without transforming its data, and
require exact modes, manifest, raw image, and padded image identities.
Canonical source and output paths must be disjoint: equality and containment
in either direction are rejected before a staging directory is created, so a
publication cannot add content beneath or around the immutable source tree.

The derived installer reconstructs and source-pins exact Photon r2 installer
machinery. It accepts only the exact named Gemini target, resolves logical
`boot2` from the live GPT, rejects an active, mounted, held, read-only, or
wrong-size target, requires battery present with `Good` health and capacity
strictly above 80 percent, requires exact Photon r2 as the current full target,
preserves a mode-0600 full backup, performs one bounded 16 MiB write, flushes,
and requires full remote and streamed local readback identity. It cannot
substitute another partition and performs no reboot, shutdown, or slot
selection.

Primary `boot`, `boot3`, preloader, NVRAM, GPT, and the whole device remain
outside the operation.

## Associated code

- `scripts/candidate_hubble.py`: exact Cassini, Photon-r2 predecessor, and
  installer-foundation pins.
- `scripts/validate-hubble-artifact.py`: complete inventory, byte, mode,
  manifest, raw/padded, and zero-tail validator.
- `scripts/build-candidate-hubble.py`: no-transform exact artifact publisher.
- `scripts/derive-installer.py`: reversible derivation from exact Photon r2
  guarded installer machinery.
- `scripts/test-hubble-contracts.py`: two-tree equality, manifest mutation,
  source/output disjointness, exact derivation, predecessor, target-write, and
  no-reboot contract tests.
- `scripts/run-hubble-transfer.py`: exact-Cassini-gated direct-USB transfer
  into volatile `/run`, one exact Photon r2 invocation, and bounded evidence
  capture.
- `scripts/test-hubble-transfer.py`: host and recovery-VM validation of the
  transfer, one-shot, volatile-storage, and forbidden-control-path contracts.

All build and validation scripts require no privileges and have no hardware
access. Only the separately generated installer has the guarded `boot2` write
path.

## Procedure

1. Validate each of the two independent exact Cassini artifact trees.
2. Publish Hubble independently from each tree into separate recovery-VM
   output roots.
3. Validate both Hubble trees and require every file byte and mode to match
   both each other and exact Cassini.
4. Derive the guarded installer, require its pinned identity, run shell syntax
   and ShellCheck, and audit its exact predecessor, target, write count, power,
   and no-reboot boundaries.
5. From known-good Gemian, install only if live-resolved inactive `boot2`
   equals exact Photon r2; preserve the full backup and require exact Hubble
   readback.
6. Shut down separately. Before asking the owner to select `boot2`, state that
   Hubble is an exact Cassini serviceability control and that any byte mismatch
   rejects attribution.
7. After boot, require exact Cassini runtime attribution and serviceability
   before transferring or invoking any transient helper.

## Observations

Two isolated recovery-VM output roots were published from the exact
hardware-passed Cassini artifact. Both contain 24 files with identical bytes
and modes, and each complete tree validates as exact Cassini. The raw and
padded hashes are respectively
`e02e2673ca054d3e4081f5234d26a394617777e8496417fd75196a948d55fa4d`
and
`febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1`.

The guarded installer was derived identically on the host and in the recovery
VM, passed Bash syntax and ShellCheck, and has SHA-256
`3adaf33fbb4567ac9ef3fd2030f85a24f69f5349f812d49493c56ded716a2452`.
The contract harness requires one bounded target write, exact Photon r2 as the
only predecessor, and no reboot, shutdown, or slot selection. It also rejects
all three canonical source/output overlap cases: equal paths, output below the
source, and source below the output.

The direct-USB runner passed nine host tests and the same nine tests in the
recovery VM. Exact Cassini BusyBox decoded the exact Photon r2 payload and
syntax-checked the generated remote program. The runtime gate requires exact
Cassini kernel, command line, configuration, helper, CPUs, handoff, childless
I2C6 counters, and USB state before it creates a mode-0500 root-owned helper in
volatile `/run`. It contains no persistent-storage, watchdog, reboot, slot,
regulator, or CPU-control operation.

From stable Gemian boot ID
`ef52abfb-7716-4cf6-b141-ae4aad297096`, the guarded installer resolved
inactive logical `boot2` as `/dev/mmcblk0p30`, required the exact Photon r2
full checksum, preserved a mode-0600 full backup, wrote one bounded 16 MiB
image, synced and flushed it, and obtained matching remote and streamed local
full readbacks. The installed Hubble checksum is
`febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1`.
No reboot, shutdown, or slot selection occurred during installation.

No device was accessed while creating or validating the artifact and transfer
contracts. Device access was confined to the separately guarded installation
recorded in
`results/install-candidate-hubble-boot2-20260727.txt`.

The owner selected `boot2`, and Hubble established exact Cassini runtime
identity with boot ID `cdd23c48-0bd3-4980-95c8-5e054be860d9`. CPUs 0--7,
handoff state, childless I2C6, and the direct USB service matched the contract.
The runner then transferred exact Photon r2 into volatile `/run`, verified its
size, hash, owner, and mode, invoked it once, removed it, and retained a
one-shot guard.

All six combined `I2C_RDWR` calls returned two messages with `errno=0`.
I2C6 transfer, DMA-start, nonzero-start, and IRQ counters each advanced from
zero to six. Nevertheless, the post tuple was exactly the six distinct
prefills:

`a1,b2,c3,d4,e5,f6 -> a1,b2,c3,d4,e5,f6`.

Each same-register pair therefore followed its different prefill:
`0x05=a1/d4`, `0x06=b2/e5`, and `0x47=c3/f6`. The boot ID, eight online CPUs,
handoff, and USB service remained unchanged. No persistent storage, watchdog,
reboot, slot, regulator, CPU-control, or `PAGE_CON` operation occurred.

## Analysis

Because Hubble's complete artifact is exact Cassini, a different Hubble boot
outcome cannot be assigned to a kernel, DTB, configuration, initramfs,
Android-v0 header, padding, or artifact-member delta. Installation integrity,
boot selection, retained device state, and run-to-run behavior remain
alternative explanations.

The transient-helper phase is deliberately separate. It may answer a DA9214
question only after the exact Cassini service boundary is re-established; it
cannot be used to retroactively attribute Photon r2's pre-serviceability
failure.

That phase now establishes that Cassini's prior zero tuple reflected its zero
receive initialization: the mainline CPU-visible receive buffer follows its
prefill even while the controller reports successful WRRD completion. The
observation does not yet distinguish wire-level input, RX-DMA destination
programming, coherency/completion, or later copyback.
The diagnostic `dma_starts` counter increments before APDMA is enabled, and
the IRQ counter observes the I2C controller interrupt rather than a separately
validated APDMA completion; neither is evidence that RX DMA wrote memory.

## Conclusion

`Partial`. Hubble restored exact Cassini serviceability and proved the
reboot-free volatile-probe workflow. Photon r2 decisively rejects the earlier
zero bytes as DA9214 contents, but the mainline I2C6 WRRD receive path must be
localized and corrected before silicon identity, provider operations, or A72
requests.

## Follow-up

Keep the current Hubble boot alive. Do not repeat Photon r2. Use a new bounded
volatile observation to distinguish WRRD receive-DMA programming/completion
from the later CPU copyback boundary, then correct that path before returning
to DA9214 identity or regulator work.
