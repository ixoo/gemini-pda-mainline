# Experiment: Cassini — direct legacy DA9214 configuration reads

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-27-da9214-direct-address-cassini` |
| Status | `completed; userspace reported zeros, RX overwrite unproven, identity gate failed closed` |
| Subsystem | MT6797 I2C6 and legacy DA9214 interface identification |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-27 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the legacy DA9214 configuration signature be read safely and repeatably
through the documented secondary I2C address without touching `PAGE_CON`?

Cassini tests exactly two passes over address `0x69`, registers `0x05`,
`0x06`, and `0x47`, using one combined register-pointer/read `I2C_RDWR`
transaction for each byte. The expected stable result on the named Gemini is
`d9 d0 c0` in both passes.

This is not a regulator-binding or Cortex-A72 experiment. The DT keeps I2C6
childless, no kernel driver owns either `0x68` or `0x69`, and the exact
Candidate AO fail-closed CPU8/9 enable method remains intact.

## Provenance and environment

- Kernel release: pinned Linux 7.1.3.
- Kernel profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-i2cdev-cassini`.
- Patch series:
  `patches/series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve`.
- Functional baseline: exact Candidate AO DT, initramfs, keymap, console,
  keyboard, USB Ethernet shell, and manual kernel-restart lineage.
- Configuration delta: `configs/gemini-da9214-cassini.fragment` enables
  built-in `CONFIG_I2C_CHARDEV`, turns the inherited DA9211 regulator and A72
  observer/provider configurations explicitly off, gives the kernel and USB
  gadget exact Cassini attribution, and retains `maxcpus=8`.
- DT delta: exact AO plus the already reviewed access-controller link and
  childless I2C6 enablement used by Candidate AR.
- Boot path: retained Planet LK Android-v0 container, owner-selected inactive
  logical `boot2`.
- Primary datasheet evidence: Renesas/Dialog
  `REN_da9213_14_15_datasheet_3v3_DST_20200219-3075819.pdf`, retained privately
  outside Git. It documents direct page-2/page-3 access through address
  `0x69`. The document is evidence, not redistributed source.
- Prior hardware evidence: the first adjacent-address probe reached `0x69`,
  but then incorrectly attempted a stateful `PAGE_CON` read instead of the
  actual configuration registers.

Exact package, configuration, compiler, helper, DTB, initramfs, Android-v0,
raw-image, padded-image, and artifact-manifest hashes must be recorded in
`results/` before installation.

## Safety assessment

Cassini's probe is read-only at the device-register semantic level. Every
transaction writes only the one-byte register pointer required for the
following read. It never writes register data.

The following boundaries are enforced by source, package, initramfs, DT, and
mutation validators:

- The probe accepts no arguments.
- It resolves only the adapter whose OF path ends exactly in
  `/i2c@1100e000`.
- The only target address is `0x69`.
- The only register pointers are `0x05`, `0x06`, and `0x47`, in that order,
  exactly twice.
- Register `0x00` (`PAGE_CON`) is absent from the transaction list.
- I2C6 has no DT children, including no DA9214 client at `0x68` or `0x69`.
- There is no A72 provider node, regulator consumer, CPU retry, `add_cpu()`,
  PSCI `CPU_ON`, voltage change, reset, isolation, SMC, or DCM operation.
- CPU8/9 retain the fail-closed `mediatek,mt6797-psci` method; `maxcpus=8`
  requests only the eight hardware-proven Cortex-A53 CPUs.
- The helper is added to the initramfs but is not referenced by `/init` or
  any inherited service. It can run only after an operator invokes it through
  the established USB or local shell.
- The initramfs probe has no storage, watchdog, reboot, power, raw-memory, or
  network-configuration interface.

Candidate construction and validation perform no device access. A separately
derived installer is pinned to exact Pioneer as the current full-`boot2`
predecessor and retains the repository's inactive-slot, backup, flush, and
full-readback requirements. Cassini alone uses the owner's explicit stable
power policy: a present battery with integer capacity from 81 through 100 and
health exactly `Good` is sufficient. AC and USB online values are recorded as
observations but never gate the write. The battery gate is sampled again
immediately before the final predecessor checksum and sole partition write,
leaving that checksum as the last target-identity gate before `dd`. AO and
global installation tooling are unchanged. The installer never reboots or
selects a slot.

Stop after unexpected heat, charging behavior, loss of the known-good boot
path, an uncommanded reset, an I2C controller fault, or any result that cannot
be attributed to exact Cassini. Do not retry an identical failed artifact.

## Associated code

- `initramfs/cassini-probe.c`: fixed-function post-USB probe.
- `scripts/build-cassini-probe.sh`: deterministic static AArch64 helper build.
- `scripts/validate-cassini-probe.py`: exact source, ELF, marker, and transfer
  contract validator.
- `scripts/build-cassini-initramfs.sh`: exact-AO-plus-one-member initramfs
  transform.
- `scripts/validate-cassini-initramfs.py`: whole-archive allowlist validator.
- `scripts/build-cassini-dtb.sh`: deterministic childless-I2C6 DT derivation.
- `scripts/validate-cassini-dtb.py`: exact whole-FDT validator.
- `scripts/validate-package-cassini.py`: manifest, series, configuration,
  image, and symbol validator.
- `scripts/build-candidate-cassini.sh`: two-pass Android-v0 construction and
  zero-padding; no hardware access.
- `scripts/derive-installer.py`: source-pinned guarded installer derivation
  after artifact hashes are calibrated.
- `scripts/test-cassini-contracts.py` and `scripts/test-cassini-dtb.py`:
  focused negative-mutation suites.

Build in the AArch64 recovery VM:

```sh
KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-i2cdev-cassini \
  ./scripts/dev-vm build-kernel

./scripts/dev-vm run \
  /mnt/gemini-pda-mainline/experiments/2026-07-27-da9214-direct-address-cassini/scripts/build-candidate-cassini.sh \
  --package /home/julien.guest/artifacts/gemini-pda/EXACT-CASSINI-PACKAGE \
  --ao-artifact /home/julien.guest/artifacts/boot-candidates/candidate-AO-mt6797-dvfsp-handoff-owner-44fc1e6a \
  --output-parent /home/julien.guest/artifacts/boot-candidates
```

Build twice from independent validated kernel packages and require recursively
identical candidate directories after normalizing only the kernel package's
documented generation timestamp.

## Procedure

### Pre-boot gate

1. Run the repository kernel-package validator and Cassini's package
   validator.
2. Build the helper twice and require byte identity.
3. Build the initramfs and final DTB twice and require byte identity.
4. Run the probe, initramfs, DT, package, LK-container, and mutation
   validators.
5. Confirm the DT is exact AO plus childless I2C6, CPU8/9 use the rejecting
   method, and `/init` is byte-identical to AO.
6. Build Cassini from two independent kernel packages and require identical
   `Image`, `Image.gz`, `System.map`, resolved configuration, DTB, initramfs,
   Android-v0 image, and zero-padded image. Record all hashes.
7. Calibrate the artifact pins and derive Cassini's installer. Validate that
   its sole accepted predecessor is the full Pioneer `boot2` SHA-256
   `c02244700fcd41a9b6a2d70e90ae2b83276f9dcdd843329643a3d9ced454779d`.
8. Apply the normal live-GPT guarded installation to inactive logical
   `boot2`, with full backup and matching full readback. The installer must
   leave the device in Gemian without rebooting. Require battery present,
   health `Good`, and integer capacity `81..100` at Cassini's immediate
   pre-write gate; retain AC and USB readings only as observational evidence.

### Hardware gate

Before boot, state the hypothesis: the direct `0x69` path should return two
stable `d9 d0 c0` signatures without affecting the established serviceability
baseline. The unique evidence is the exact six-transaction Cassini helper;
no earlier candidate issued this sequence.

1. The owner manually selects `boot2`.
2. Confirm a readable correctly rotated console, working keyboard, and exact
   Cassini USB gadget identity.
3. Connect to the USB Ethernet shell. Record `uname -a`,
   `/sys/devices/system/cpu/online`, the absence of CPU8/9 online controls,
   I2C6's OF identity, and that no I2C child is bound.
4. Wait until the DVFSP handoff and childless I2C6 readiness markers pass.
   Do not run the probe before USB serviceability is established.
5. Invoke `/bin/cassini-probe` once, with no arguments.
6. Capture the complete stdout and kernel-log marker sequence. A successful
   run contains:

   ```text
   GEMINI_CASSINI_PROBE_BEGIN adapter=i2c-N of=/i2c@1100e000 address=0x69 passes=2 registers=0x05,0x06,0x47
   GEMINI_CASSINI_TRANSACTION_BEGIN pass=1 register=0x05 transaction=1 address=0x69 messages=2
   GEMINI_CASSINI_READ pass=1 register=0x05 value=0xd9 transaction=1
   GEMINI_CASSINI_TRANSACTION_BEGIN pass=1 register=0x06 transaction=2 address=0x69 messages=2
   GEMINI_CASSINI_READ pass=1 register=0x06 value=0xd0 transaction=2
   GEMINI_CASSINI_TRANSACTION_BEGIN pass=1 register=0x47 transaction=3 address=0x69 messages=2
   GEMINI_CASSINI_READ pass=1 register=0x47 value=0xc0 transaction=3
   GEMINI_CASSINI_TRANSACTION_BEGIN pass=2 register=0x05 transaction=4 address=0x69 messages=2
   GEMINI_CASSINI_READ pass=2 register=0x05 value=0xd9 transaction=4
   GEMINI_CASSINI_TRANSACTION_BEGIN pass=2 register=0x06 transaction=5 address=0x69 messages=2
   GEMINI_CASSINI_READ pass=2 register=0x06 value=0xd0 transaction=5
   GEMINI_CASSINI_TRANSACTION_BEGIN pass=2 register=0x47 transaction=6 address=0x69 messages=2
   GEMINI_CASSINI_READ pass=2 register=0x47 value=0xc0 transaction=6
   GEMINI_CASSINI_PROBE_PASS first=d9,d0,c0 second=d9,d0,c0 transactions=6 page_con=untouched
   ```

   The helper refuses to issue any I2C transfer unless `/dev/kmsg` is open and
   the probe-begin and matching transaction-begin write has returned success.
   Each post-read write must likewise return success before another transfer.
   Cassini later proved that this fail-closed write contract is not a retention
   contract: Linux accepted all writes but retained only the default burst of
   ten and explicitly suppressed the final four lines. A future fault probe
   must account for printk rate limiting instead of treating a successful
   `/dev/kmsg` write as durable-marker proof.

7. Confirm console, keyboard, USB shell, and CPUs 0--7 remain functional
   after the probe.
8. Type bare `reboot` once and confirm the already proven MT6797 kernel-native
   restart returns to Gemian. No countdown or automatic watchdog is part of
   Cassini.
9. Collect pstore immediately, verify the changed boot ID, and verify the
   complete logical-`boot2` readback still matches the installed Cassini
   padded checksum.

One attributable run is sufficient for the decision gate. Repeat only if the
first run is inconclusive and a new observation can distinguish the outcomes.

## Observations

Two independent kernel packages and candidate trees reproduced all
boot-bearing bytes. The full-readback-verified image
`febe4d44b14b899cb357fae1b3ecda9bdb687c0c3e1f9e4b3cee30bc04f13cf1`
booted from logical `boot2` on the named Gemini. The owner observed the
expected delayed console. The exact Cassini kernel, USB identity, eight A53
CPUs, ready DVFSP handoff, preserved AP-DMA, childless I2C6 adapter, and zero
prior transfers were confirmed before invocation.

The one permitted helper invocation completed all six combined transactions.
Userspace reported `00 00 00` in both passes, then the helper failed the
expected signature with exit status 2. I2C6 counters advanced from zero to
exactly six transfer attempts, DMA starts, nonzero starts, and IRQs. There was
no transport error, reset, handoff fault, USB loss, CPU regression, storage
access, regulator operation, or A72 request.

The complete sequence was retained in live USB-shell stdout. Ramoops retained
the first ten `/dev/kmsg` probe lines and
`printk: cassini-probe: 4 output lines suppressed due to ratelimiting`,
matching `printk_ratelimit=5` and `printk_ratelimit_burst=10`. This directly
invalidates the assumption that successful `/dev/kmsg` writes prove every
line was retained. Bare native reboot returned to Gemian with a changed boot
ID; pstore retained the candidate prefix and reboot request, and the
post-return full logical-`boot2` checksum still matched Cassini.

Exact build/install evidence is in
[`build-install-candidate-cassini-20260727.txt`](results/build-install-candidate-cassini-20260727.txt).
The complete runtime decision record is in
[`runtime-candidate-cassini-attempt-1-20260727.txt`](results/runtime-candidate-cassini-attempt-1-20260727.txt).
The subsequent Gemian and RX-buffer reconciliation is in
[`gemian-da9214-live-dump-reconciliation-20260727.txt`](results/gemian-da9214-live-dump-reconciliation-20260727.txt).

## Analysis

The expected stable `d9 d0 c0` bytes are interface/configuration fields, not a
silicon device ID. Two independent retained Gemian boot logs show those exact
live page-2 values and successful DA9214 detection. Cassini proves that six
bounded direct transactions at `0x69` completed reproducibly, but not that the
receive DMA overwrote userspace's pre-zeroed bytes. `I2C_RDWR` copied each
initial zero into the kernel receive buffer, and the MT65xx driver mapped that
buffer for receive DMA; a completed transfer which did not overwrite it is
therefore observationally identical to a received zero. Cassini does not
establish a DA9214 identity or authorize a driver bind.

The next decision gate is neutral Candidate Photon r2: retain the exact
Cassini kernel/DT/configuration and the exact six `I2C_RDWR` request/message
sequences Cassini issued, but
initialize each receive byte immediately before its transaction to a distinct
nonzero prefill and always complete both passes after successful transfers.
The paired observations distinguish equal post tuples across two different
prefill tuples, including a tuple byte that equals one transaction's prefill.
All-zero, `d9 d0 c0`-twice, equal-prefill, mixed, and ioctl-result-not-two
branches preserve objective pre/post evidence without attributing a byte to
the device, controller, or DMA. Photon r0 was installed and fully read back,
but review superseded it before any boot or probe invocation. Photon r1 fixed
the control-flow ambiguity and was reproduced, then its causal output labels
were superseded before installation.

## Conclusion

`rx-overwrite-unproven`: the direct `0x69` transport completed six bounded
transactions and userspace reported zero, but the pre-zeroed receive buffers
make those values ambiguous. The identity gate correctly failed closed. Do
not repeat Cassini unchanged and do not add a provider or A72 activation based
on this result.

## Follow-up

Run Photon r2 as the initramfs-only pre/post successor. It adds a durable,
decision-changing paired-prefill observation while retaining Cassini's exact
kernel/DT/configuration and six-read request protocol. Keep its persistent
attribution within the observed printk burst. Do not boot superseded r0 or
install superseded r1. Provider binding, voltage changes, CPU8 activation, and
the active A72 power sequence remain blocked until the r2 pre/post gate is
resolved.
