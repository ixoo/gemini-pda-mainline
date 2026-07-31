# DA921x unmatched-compatible client discriminator

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-30-da921x-unmatched-client` |
| Status | `attempt 1 serviceable; real-compatible path implicated` |
| Subsystem | regulator, I2C, arm64 Device Tree |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-07-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does the pre-serviceability failure occur for any instantiated `0x68` I2C
client with the child’s existing resource contract, or only when the real
`dlg,da9214-legacy` compatible/modalias can match the DA921x module?

The candidate starts from the exact failed enabled-child module-profile
artifact. It preserves the kernel, config, initramfs, module bytes, child
status, address tuple, resource properties, Android header, and LK placement.
Its sole semantic delta changes the child compatible from
`dlg,da9214-legacy` to deliberately unmatched `dlg,da9214-unbound`.

## Decision

- Serviceability with an unbound `0x68` client implicates real-compatible or
  modalias matching rather than generic client creation.
- Another pre-serviceability failure implicates generic I2C-client
  instantiation or the child’s resource/dependency contract.
- The module must not be loaded. Neither result permits a provider or A72
  request.

## Safety

No kernel module advertises the diagnostic compatible. The initramfs has no
`/sbin/modprobe`, and the embedded module remains at its manual-only path.
Runtime collection is read-only and must not bind a driver, trigger an I2C
transfer, or access a device partition.

## Observations

The source-pinned derivation produced raw candidate
`6c19001a8f045ae63d5855cc426581ef636418f66ce3fa5ba80b63bedab607bd`
and exact 16 MiB boot2 image
`117ab7b953fb20023738ad5b936b14b100b7cc6b25d9ee5daf7db7df720656d2`.
The appended DT is
`be4a2bd3f52803d629b38a5d7f8971a72a9877de83c7b6c74e31c8fc6989f756`.
All 32 LK/container gates passed. DT validation confirmed that the address
tuple remains `0x68,0x69`, the child remains enabled, and the sole semantic
delta is the compatible change to `dlg,da9214-unbound`.

See [offline validation](results/offline-validation.txt) and the
[pre-boot hypothesis](results/pre-boot-hypothesis.txt).

The guarded installer resolved logical `boot2` as `/dev/mmcblk0p30` from the
live GPT while Gemian boot ID
`5e8310c7-95b1-46e9-a68f-026a3c360ebe` was active. The exact predecessor
checksum matched. It wrote the padded candidate, synchronized and flushed it,
then required both a matching on-device full-partition checksum and an
independent 16 MiB byte comparison. Both matched
`117ab7b953fb20023738ad5b936b14b100b7cc6b25d9ee5daf7db7df720656d2`.
No new backup was created under the project’s standing backup policy. The
temporary readback was removed and the device’s shutdown was confirmed. See
[installation result](results/install-boot2-20260730-1905.txt).

## Attempt 1

The owner selected `boot2` once and observed the console start. The USB gadget
enumerated with its exact identity, and its direct netcat shell became
serviceable after the host address was restored.

Runtime identity was `7.1.3-gemini-da921x-mod` on boot ID
`0bd827dd-cad6-40ef-9bde-438b7b32040e`. CPUs 0--7 were online, CPUs 8--9
remained offline, USB was configured/up, the keyboard and tty1 were present,
and the active console was ttyS0.

The enabled DT child had exact compatible `dlg,da9214-unbound` and the
unchanged `0x68,0x69` address tuple. Exactly one `1-0068` client existed with
modalias `of:NregulatorT(null)Cdlg,da9214-unbound`; it was unbound. I2C6
handoff was ready with one successful initialization and zero transfer,
DMA-start, nonzero-start, and IRQ counters. Every lifecycle-oracle counter was
zero.

No DA921x symbol, module, driver directory, or identity log existed. The
manual-only module file retained its exact checksum, `/sbin/modprobe` was
absent, and no module load, bind, I2C trigger, or partition access was
performed. The validated native reboot returned the device to Gemian
`3.18.41+` with new boot ID
`189deafa-09eb-4395-a88b-e77868741fbf`. See
[runtime result](results/runtime-candidate-unmatched-attempt-1-20260730.txt).

## Conclusion

Attempt 1 passes the serviceability gate. Relative to the failed enabled-child
module-profile candidate, its sole semantic change was the compatible string.
The successful creation of an enabled, unbound `0x68` client with the complete
resource contract rules out generic client creation and that unchanged
contract as sufficient causes. The remaining failure boundary is specific to
the real `dlg,da9214-legacy` compatible/modalias path.

This result does not prove that the manual-only module executed in the failed
boot; the serviceable run proves that it was not resident here, and the
initramfs has no automatic invocation path. The next discriminator must remove
the module file entirely while restoring the real compatible, preserving the
same kernel/configuration. The exact unmatched candidate must not be repeated.
