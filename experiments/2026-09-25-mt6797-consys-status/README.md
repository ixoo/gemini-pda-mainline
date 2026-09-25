# Passive CONSYS power-status gate

Status: kernel and private image validated; guarded boot2 installation and
clean-shutdown request complete. Owner boot2 selection and mainline result are
pending.

The first Wi-Fi hardware question is whether retained firmware leaves CONSYS
powered at mainline late init. The working Gemian boot is an active-WLAN
reference, so its enabled `pg_conn` clock does not answer that handoff question.
The retained MT6797 sequence identifies CONN bit 1 in both SPM power-status
registers at offsets `0x180` and `0x184`; see the
[power-domain analysis](../2026-09-05-mt6797-wifi-contract/POWER_DOMAIN.md).

[Patch 0545](../../patches/v7.1.3/0545-soc-mediatek-observe-MT6797-CONSYS-power-status.patch)
uses the existing SPM syscon, already shared by the A72 platform-state reader,
to read those two registers twice during late init on Gemini. It classifies
only the CONN bit as `off`, `on`, `mixed`, `moved`, or `unavailable`. It makes no
power, reset, remap, firmware, radio, or DMA request and never treats a status
as an ownership grant. It is default-off outside the named
[`mt6797-a53-consys-status-snapshot`](../../kernel/manifest.json) profile,
which retains the tested A53 service foundation and its RAM-boot facilities.

## One-boot decision

Use one guarded boot2 image assembled from the validated package and the
accepted RAM candidate. The previous board tree lacks the syscon compatible,
so the [composition recipe](build-candidate.py) adds exactly that one property;
its decoded-tree comparison rejects every other tree change. The kernel and
exact RAM release gate also change; the other 46 RAM members remain byte-identical.
Authenticate the mainline boot and preserve its complete log before
recovery. The unique measurement is the single `mt6797-consys-status` line
bound to that boot identity and candidate hash.

- Stable `off` in both reads permits designing a separately reviewed shared
  CONSYS/EMI/AP-DMA owner; it does not authorize activating the radio.
- `on`, `mixed`, or `moved` means the handoff is not an attributable cold-off
  state. Stop active Wi-Fi bring-up and investigate the retained owner.
- `unavailable`, a missing record, or an unverified boot identity makes this
  boot inconclusive. Diagnose the observation path before any new boot.

Do not repeat an identical image without a decision-changing measurement.
The owner selects boot2 physically after the guarded write and clean shutdown.
Use the established authenticated USB/RAM collector and reviewed return path;
confirm changed-boot Gemian afterward.

This gate establishes neither usable Wi-Fi nor the shared manager, firmware
load, station association, or traffic. Those require separate implementation
and measured device tests under the [shared owner contract](../2026-09-05-mt6797-wifi-contract/SHARED_OWNER_IMPLEMENTATION.md).

## Offline result

Buildbox built and validated commit `b3d26e15bc7f90049e919591b97ecf06f77fb0d3`
for this profile against pinned Linux 7.1.3. The package inventory is
`67e2a0b3110bab959e2d973de17686ae14bb43e69f22509faab51e4bf7192599`;
the kernel release is `7.1.3-gemini-consys-status-snapshot`. Its configuration
selects the observer and leaves `MTK_SCPSYS` disabled. The observer is present
in the linked `System.map`. Pinned checkpatch passes with the internal patch's
intentional non-certifying sign-off and new-file notices excluded. No DT schema
changed in this selected series.

The [private-image receipt](results/candidate.json) records the exact accepted
parent, kernel package and output hashes. The validated Android-v0 boot image
is 9,132,032 bytes; the 16 MiB padded boot2 image has SHA-256
`83cedf98881e05b4552cd5747611cc44a2b0bbc3feaa299a6ed8d92489175060`.
The builder checked the package inventory, decompression, required symbols,
complete parent identity, CPIO round trip, one-property DT delta, LK format,
payload pairing and zero-padded partition size. The image contains a private
authentication key and remains ignored under `artifacts/`. Composition itself
had no device effect.

## Bound deployment and collection

The [installer adapter](installer.py) derives the previously reviewed guarded
boot2 installer for this exact receipt and a freshly observed Gemian boot ID.
It verifies the seven private candidate files and full 16 MiB padding, then
retains live-GPT selection, block identity guards, inactive target checks,
stable-power check, predecessor hash, single write, full readback and clean
shutdown. The generated shell passes `bash -n` and ShellCheck. Its default
adapter actions only prepare or validate offline; execution is a separate
explicit action after live identity checks.

The [session binding](session.py) reuses the accepted authenticated RAM
collector and exact kernel-release checks. The [host runner](host.py) calls the
established bounded observation, identity probe, log seal/export, evidence
readback, native recovery request and changed-boot Gemian watcher. Its one
session has one connection each for observation (45 s), identity (15 s), log
export (30 s) and recovery request (15 s), plus the reviewed 180 s Gemian
return window. An occupied or interrupted session is consumed; a missing
status line or incomplete log is inconclusive, not a reason to retry the same
image. An offline synthetic receipt verified the new host binding without
device access.

The [sanitized deployment receipt](results/deployment.json) records one
installation from Gemian boot `5302713c-4108-464e-b5e9-d975e6ba0164`. The
live GPT selected inactive `boot2`; the reviewed block-device guard passed
against a distinct root, battery was 94% with good health, and the prior full
partition checksum matched the tested A53 service image. The new padded image
was written, synced, flushed and fully read back with matching SHA-256. The
installer requested clean shutdown and confirmed the host became unreachable.
The private full deployment receipt remains ignored. The owner has not yet
reported physical boot2 selection, and no mainline Wi-Fi status result exists.
