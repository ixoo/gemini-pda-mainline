# Mainline EMI read-service positive control

The [previous passive boot](../2026-09-27-mt6797-emi-boot-observe/results/runtime-1.json)
returned zero for both range and policy reads of regions 18, 19 and 23.
Gemian reported those regions programmed in its subsequent, separate boot.
The public vendor wrapper passes a register offset in x1 to SMC32
`0x82000208`, matching the mainline probe's call shape, but the selected
source is not byte-matched to the executing secure firmware. The zeros are
therefore insufficient to adopt or reject a hardware protection policy.

The named `mt6797-a53-emi-range-census` profile adds one read-only patch to
that exact passive owner. After the checked-OFF CONN query and existing VCN28
and EMI samples, it makes 24 bounded SMC reads of the vendor-defined range
registers for regions 0 through 23 and logs one raw word per region. The
three bank bases and eight-register stride come from the pinned MT6797
[`emi_mpu.h`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h).
It makes no SET/WRITE call, protection change, power transition, reset,
radio request, firmware load or memory access to a protected window.

## One-boot decision

Hypothesis: at least one range programmed before the passive owner probe is
readable through the same secure service in mainline. The unique measurement
is exactly one census record for each of 24 regions in a complete sealed log,
with the exact candidate and changed boot ID, the existing region-18/19/23
samples, a passing A53 regression and a confirmed changed-boot return to
Gemian. A malformed, duplicate or missing record rejects the observation.

If any raw range is nonzero and the 24-word vector is not uniformly
`0xffffffff`, the read path has a same-boot positive control. Compare
region 18/19/23
with the prior boot without treating separate boots as one state. If all
24 are zero, the read service still lacks a positive control: distinguish
an unprogrammed early state from service behavior through retained-handler
analysis or an instrumented Gemian reference before choosing a policy. An
unsupported signature or failed regression rejects the candidate. No branch
establishes master/domain routing, region overlap, exclusive writers or
permission to issue an EMI write. Do not repeat this candidate without a
decision-changing modification.

Only a clean pushed Buildbox package may become a boot2 candidate. Reuse
the boot-tested DTB/initramfs/config, validate the LK container and exact
16 MiB image, then use the reviewed live-GPT boot2 guard and matching full
readback. The owner selects boot2 physically after the finite collector is
armed. Complete logs and device-specific material remain ignored private
evidence; publish only sanitized receipts.

The patch is an internal experiment with synthetic non-certifying authorship,
not an upstream submission.

## Retained secure-read path

A bounded, read-only [static check](results/retained-read-service.json) of the
hash-pinned retained TEE image found SMC32 `0x82000208` dispatching the low
32 bits of x1 to an EMI read helper. The helper accepts offsets `0x160` through
`0x3bc`. Ordinary offsets read the 32-bit register at `0x10200000 + offset`;
four exception offsets (`0x3a4`, `0x3ac`, `0x3b4`, `0x3bc`) read cached words
instead. All 24 census range offsets are accepted ordinary reads. The previous
region-18/19/23 range samples were also ordinary reads, but its region-23
policy sample at `0x3bc` was cached, so that policy value was not a direct
hardware-register observation. Capstone decoding and independent GNU AArch64
objdump checks agree on the bounds and read paths. The private image and
disassembly remain in the RE VM; only window hashes and independently written
semantics are published.

This narrows interpretation **if** that exact secure handler ran in the
mainline boot. The retained file and historical matching slot hashes do not
establish the executing secure-firmware identity. Neither static analysis nor
an all-zero census alone proves a mainline EMI protection policy, domain
routing or overlap behavior.

The pinned Gemian Wi-Fi reference source at
`59e00a9144d782e148332009a835b99c43382467` already implements its
`mpu_config` reader through `mt_emi_reg_read()`. For MPU offsets, the
[`emi_reg_rw.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/emi_mpu/emi_reg_rw.c)
implementation (SHA-256
`da41e7d325aa4d3207a38bd566f39680a3b2275db87b4ba0919d266375d858e0`)
routes that call to
[`emi_mpu_smc_read()`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_secure_api.h),
which uses the same SMC32
`0x82000208` with the offset in x1. The selected configuration has
`CONFIG_MTK_PSCI=y`, and the header bounds its MPU offsets to `0x160..0x3bc`.
The earlier [carrier-up Gemian sysfs reference](../2026-09-26-mt6797-emi-active-reference/results/runtime.json)
therefore has a source-supported secure-read path and nonzero range values;
its stock running kernel was not byte-matched to that source, so this is not
an authenticated SMC-call trace for that boot. A new instrumented Gemian
kernel solely to invoke the same read service is not selected. The installed
mainline census still supplies the missing same-boot range control if its
device session can be established.

## Built candidate

Clean pushed commit `68e21a5f` built 545 selected patches on Buildbox. The
fetched package passed its full inventory validation; the [build receipt](results/build.json)
pins the package, Image.gz and unchanged configuration identities. Strict
Checkpatch found no source warning or check; the synthetic patch intentionally
lacks a certifying DCO sign-off. The [candidate builder](build-candidate.py)
verified the package and reused the exact boot-tested EMI observer DTB,
initramfs and configuration while replacing only `Image.gz`. The LK container
and exact 16 MiB padding passed validation. The sanitized
[candidate receipt](results/candidate.json) pins full boot2 SHA-256
`98269081c35d13476aaeb95f503f30a680dd2cb1ee8ad5766edae90e8a56a525`.
These checks do not imply a device installation.

The [installer wrapper](install-passive.py) requires the exact preceding EMI
observer image and uses the reviewed live-GPT boot2 guard and full-partition
readback. The [host collector](passive-host.py) preserves the existing owner,
VCN28, three EMI and A53 checks and requires exactly 24 unique census
records in the complete log. Positive, all-zero, duplicate and uniform
`0xffffffff` parser fixtures passed. The finite [USB watcher](watch-boot.py)
waits for the owner's physical boot2 selection after installation and clean
shutdown.

## Deployment and USB watches

The guarded installer resolved logical boot2 to `/dev/mmcblk0p30`, confirmed
the known-good Gemian root was `/dev/mmcblk0p29`, stable power and the exact
preceding EMI observer checksum, then wrote, flushed and fully read back the
census image. The readback matched the candidate and Gemian shut down cleanly.
The sanitized [deployment receipt](results/deployment.json) pins those facts;
the full installer and deployment summary remain ignored private evidence.

The first 900-second [USB watch](results/watch-1.json) saw MediaTek
`0e8d:20ff` three seconds after arming, then expired at that stage with no
mainline gadget and no device SSH attempt. A post-expiry host read still saw
that USB ID, and the known-good Gemian LAN SSH endpoint timed out. No kernel
log or EMI census exists for this attempt. USB enumeration alone cannot tell
whether the owner reached the boot menu, selected boot2 or where startup
stopped. The physical screen state is pending; a timeout does not authorize
another boot, write or recovery path.

The owner then reported boot2 started. A second 900-second
[watch](results/watch-2.json) was armed after that report, already at
`0e8d:20ff`. It recorded no USB transition and expired with no mainline route
or device SSH attempt. The post-expiry USB ID remained `0e8d:20ff`, while the
known-good Gemian LAN endpoint timed out. This does not establish the screen
state or a candidate-kernel failure. No new boot or recovery action is selected
without the owner's screen observation.

The owner later identified the black screen and persistent `0e8d:20ff` as a
powered-off charging state. A physical power-on reached a new known-good Gemian
boot; its root was `/dev/mmcblk0p29`, and a full read of boot2 still matched the
installed census image. Gemian was then shut down cleanly. The third finite
[USB watch](results/watch-3.json) recorded a fresh preloader enumeration after
that shutdown, followed by `0e8d:20ff` and no mainline route through expiry.
This establishes a new startup but does not establish physical boot2 selection
or candidate execution at expiry. The owner's screen observation was pending; no
repeat boot or recovery action followed from the USB timeout alone. The owner
subsequently confirmed boot2 selection, and its mainline USB gadget appeared
after the watch had expired.

## Authenticated census and return

The [host collector](results/runtime-1.json) then claimed the exact installed
candidate in mainline boot `79d60a88-fd9d-4986-aa81-f3cf8cefa506`. Its
complete sealed kernel log contains exactly 24 unique range records. Twelve
regions (1, 2, 7–14, 16 and 17) returned nonzero values through the secure
read service in the same boot where regions 18, 19 and 23 returned zero for
their range and sampled policy offsets. The VCN28 control remained `0x1a60`
with on-control clear; the provider probe and A53 service regression passed.
The reviewed native recovery returned to changed-boot Gemian.

One bounded, read-only `mpu_config` read in that returned Gemian boot found
`wlan0` up with carrier and the same boot ID before and after. Converting the
reported 64-KiB range bounds to register words, 20 of 24 regions match the
mainline census. Only regions 18, 19, 22 and 23 differ: they were zero in
mainline and programmed in carrier-up Gemian. The raw log and Gemian response
remain ignored private evidence with hashes in the sanitized receipt.

This is a same-boot positive control for the mainline read path, so its zero
region-18/19/23 values are not explained by a read service that uniformly
returns zero. The Gemian comparison is across boots and does not identify the
writer or timing of those regions, effective master/domain routing, overlap
priority, or authority to write an EMI policy. Retained secure-firmware bytes
still are not attested as the executing image. The next owner design must
account for these unresolved facts before an effect-bearing Wi-Fi transition.

## Pinned Gemian source attribution

A read-only check of the prepared Gemian source tree at
`59e00a9144d782e148332009a835b99c43382467` found a likely producer for
the fourth differing range. Its
[`scp_helper.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/scp/mt6797/scp_helper.c#L743-L761)
(SHA-256 `fa5778ab866b48da9fc83ff5e8a415eb9f21ca8604d285d0d4080e5182f3bbed`)
assigns region 22 to SCP shared memory and requests protection over its
reserved-memory base and size during SCP helper initialization. The
[recorded Gemian reservation](../../docs/hardware/gemini-gemian-baseline.md#firmware-reserved-memory-observed-at-boot)
is `0x8f000000+0x01000000`, exactly the `0x8f000000..0x8fffffff`
region-22 bounds observed on return. The source-to-running-kernel match is
not attested, and the sysfs range does not identify the writer by itself;
region 22 does not overlap the CONSYS window.

The same source tree's
[`ccci_platform.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/eccci/mt6797/ccci_platform.c#L60-L130)
(SHA-256 `d7092013b0fa14b12c37e96a973c3179c565c1a1e1ebef3a6c27ec38b566a156`)
labels MPU permission domain 2 `CONN` in both its field-order comment and
default-permission table. This identifies the vendor source's intended
domain label, not the actual domain carried by a WLAN transaction. The
current Gemian boot ID was unchanged across a bounded read-only search of its
kernel log; no matching region-22/23 producer line appeared. That absence
does not override the source or prove no write occurred. Master routing and
region-23 applicability remain the decision gates for a mainline EMI writer.
