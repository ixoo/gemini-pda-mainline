# Observed Gemian modem memory handoff

## Result

One known-good Gemian boot joins the loader's v2 metadata, saved initialization
log and OS reservation map. It supplies actual MD1/MD3 image-memory and shared
region placement rather than the static DTS size defaults. The
[source-only handoff audit](MEMORY_HANDOFF.md) can now be narrowed accordingly.
This remains vendor-OS evidence, not a mainline modem result or an admitted
memory mapping, radio operation or release procedure.

The [sanitized receipt](results/gemian-memory-handoff-20260908.json) records the
three invocations, stable boot identity, complete configuration digest, selected
configuration values, decoded properties and exact selected saved-log lines.
Gemian was `3.18.41+`, AArch64, Debian 9, rooted on `mmcblk0p29`. No boot,
partition, modem-control, firmware, register or protection operation was issued.

## Joined observations

The live chosen node contains `ccci,modem_info_v2` and no v1 property. Interpreted
with the pinned source structure, its 48 bytes report an LK buffer at
`0x88000000`, used size `0xa20`, tag version 2, 22 tags, loaded flags `0x5` and
zero aggregate/per-modem errors. The saved log independently prints the same
buffer address, size and tag count and selects the utility's `using v3.` path.
That diagnostic names the utility path; it does not change the tag version.
The read-only `lk_md` attribute reports enabled status `0x1` and load success.
These are loader/host reports, not a secure-side verification result.

| Region | Saved-log base | Saved-log size | OS reservation evidence |
| --- | ---: | ---: | --- |
| MD1 image memory | `0xb4000000` | `0x08000000` (128 MiB) | Inside the larger `mblock-6-ccci` reservation |
| MD3 image memory | `0xbe000000` | `0x00c00000` (12 MiB) | Matches `mblock-7-ccci` |
| AP–MD1 shared | `0x88000000` | `0x00200000` (2 MiB) | First third of `mblock-5-ccci` |
| MD1–MD3 shared | `0x88200000` | `0x00200000` (2 MiB) | Middle third of `mblock-5-ccci` |
| AP–MD3 shared | `0x88400000` | `0x00200000` (2 MiB) | Final third of `mblock-5-ccci` |

The actual reserved nodes use `mediatek,ccci`, concrete `reg` properties and
different names from the static source DTS. `mblock-5-ccci` is 6 MiB at
`0x88000000` with `no-map`, outside the reported System RAM resources.
`mblock-6-ccci` is **160 MiB**, not 128 MiB, at `0xb4000000`; the next 12 MiB
node begins at `0xbe000000`. Neither image reservation has `no-map`. Both lie
within a System RAM resource, but the kernel's retained memblock reservation
metadata covers their combined `0xb4000000–0xbebfffff` interval. Absence of
`no-map` is therefore not evidence that the image allocations were available
to ordinary allocation. This does not prove a safe later release operation.

The 32 MiB tail at `0xbc000000–0xbdffffff`, beyond the logged MD1 memory
requirement but within its DT reservation, remains unattributed. Preserve the
whole reservation; do not shrink it to the image's requirement or assign the
tail to another consumer. The subsequent [retained-loader audit](LOADER_TAIL.md)
finds a deferred-reclamation mechanism consistent with this tail, while leaving
the actual boot's tags and safe release unresolved. The AP–MD1 shared size is
now observed as 2 MiB on this boot; the older 1 MiB device-property inventory is
not its active layout.

The saved MD1 check-header report identifies version 5, 344 bytes, `ulwctg`,
`MT6797_S00`, build `MOLY.LR11.W1630.MD.MP.V105.8`, and a reported raw image size
of `0x0116113c`. Its memory requirement agrees with the 128 MiB loader record.
This identifies the reported header, not the exact running-image digest;
neither firmware nor modem memory was read to establish such a digest.
The subsequent [retained-firmware join](RETAINED_FIRMWARE.md) finds matching
reported header fields in the July capture and pins its component container
digests. That comparison does not attest the running bytes.

## Protection evidence and limits

The saved log records the ready branch skipping ROM/RW remap and image load,
while still logging shared remap from `0x88000000` to modem view `0x40000000`.
It also records an AP–MD1 protection request for region 7 at
`0x88000000–0x881fffff` and two staged region-13 requests for
`0xb7460000–0xb882ffff`, with attributes `0x16db44` and `0x16db64` respectively.
This agrees with the asymmetric host-side ownership found in the source audit.
The messages precede the relevant calls; they do not witness accepted secure
MPU programming or a readback. No protection-register read was performed.

The remaining handoff gaps are the exact loaded-image identity, attribution of
the extra 32 MiB reservation, secure MPU acceptance/lock authority and a safe
release lifetime shared with MD3. Further copies of unchanged OS metadata will
not resolve those gaps. Prefer attributable retained loader/firmware evidence;
any new effect-bearing acquisition still needs its own admitted protocol.
The full queue/DMA, framing and boot/crash teardown gates remain incomplete.

## Acquisition and validation

After confirming that the previous device tasks were stopped and custody was
released, `/root` performed one identity connection and two identity-bracketed
read-only collections. They read ordinary DT/configuration/mount/resource
metadata and existing kernel log text, then the source-reviewed `lk_md` getter,
memblock reservation listing and one 32 KiB prefix of `/proc/ccci_dump`.
The latter copies existing buffers using per-open cursors; it does not trigger
a hardware dump or clear the producer log. The selected source files and
read-method review are pinned in [the access receipt](results/gemian-handoff-access-sources.json).

The prefix is deliberately incomplete. The ring portions can change while
being read, so it is not an atomic modem-state snapshot or a full boot/crash
history. The older initialization lines and corroborating OS metadata support
the bounded address/header observations above. No missing line is treated as
proof that an operation did not occur. The consumed LK tag pointer was never
dereferenced, and `/proc/ccci_log` was not opened.

Raw streams, the complete prefix and command packets remain private and
access-restricted. Published selections omit kernel virtual pointers and
unrelated radio/runtime records. All SSH commands returned zero with only the
same legacy key-exchange warning. The boot ID was unchanged throughout; device
custody is released with Gemian left running. Property decoding, interval
containment and selected-line provenance were checked, and the common repository
gate passed. No kernel build or hardware-support test was performed.
