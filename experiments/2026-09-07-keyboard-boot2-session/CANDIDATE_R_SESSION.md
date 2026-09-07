# Candidate R first-boot handoff

Status: **installed and shut down; waiting for one owner boot2 selection**.
Device custodian: the primary integration coordinator.  No other live-device
operation may overlap this handoff.

## Frozen candidate

- Private directory:
  `candidate-3290b867bc6cb2ecee42e6ca1436e1ae29613c074e7e45b3836ecb2905f3e07c`
- Raw Android-v0 image:
  `3290b867bc6cb2ecee42e6ca1436e1ae29613c074e7e45b3836ecb2905f3e07c`
- Exact 16 MiB boot2 image:
  `29f59c7f21a25b47d63d653857db9d7d0760d9a00f7193e098219699235f16f1`
- Private manifest:
  `62440fdee9267e26d6f90148609a7c2551fdb9d6a9f603da03f891638c65180d`
- Derived guarded installer:
  `a092f8ea091e04ffea75d406a60220a4bae5fa5808d359989a96eb6a2f7dc068`

The independent specialist review accepted this as a meaningful new
observation candidate because its current authentication bundle restores a
durable host-key-pinned path.  The reviewer independently passed all seven
candidate identities, exact padding, the complete 47-member validator, installer
derivation, Bash syntax and ShellCheck.  The credential-only explanation stays
an inference, and no historical runtime result transfers.

## Installation admission

The custodian may perform one reviewed temporary deactivation of the exact
unused Gemian zram swap entry, then one guarded installer invocation on the same
boot.  The device must be known-good quiescent Gemian with stable external power.
The installer must resolve logical boot2 from the live GPT; require the target
inactive, unmounted, writable and distinct from root; record its predecessor;
write only the Candidate R padded bytes; verify a complete matching readback;
remove private staging; and request clean shutdown.  It must never reboot or
substitute another partition.  A failed or indeterminate prerequisite stops
before installation.  A confirmed deactivation followed by pre-install abort
uses the single reviewed restoration path.

The admitted prerequisite completed on Gemian boot
`2b2a317f-94ff-43b3-a51f-2fa6c5ba0bf9`: both fresh samples passed, the unused
zram entry was removed, and `MemAvailable` remained 3,118,748 KiB. The guarded
installer then resolved boot2 as `/dev/mmcblk0p30`, distinct from root
`/dev/mmcblk0p29`, and replaced predecessor
`08fc061475b4bd6bc274bef6cb61c6e0a1cb8d786c5be197b79dba006bebb1c2`.
Write, sync, flush and independent full readback matched Candidate R's padded
digest. Private staging and readback were removed, the shutdown request was
issued only after evidence flush, and the bounded follow-up found the device
unreachable. No reboot or fresh predecessor backup occurred.

## Owner action after verified shutdown

Keep the USB data cable connected.  Power on with the established silver-button
boot2 selection during LK startup.  Make one selection only.  Expect the
“Gemini A53 authenticated baseline” screen and SSH-key-only administration
notice within 60 seconds.  Report the screen here without typing commands or
testing keys.  Unexpected heat, charging behavior, reset loops or an unreadable
screen stops the session.

The custodian then has one prompt fresh baseline observation using Candidate R's
current pinned host key and administrator key.  It must bind the new boot ID,
kernel/config, CPU0-7 online and CPU8-9 offline, USB, console/map/input metadata,
reader exclusion and the existing RAM logger.  Pass permits later review of the
separate harmless disconnect proof.  Failure or inconclusive evidence stops and
uses the reviewed preservation/recovery branch.  Neither disconnect proof nor
the 20-case keyboard capture runs during this baseline.
