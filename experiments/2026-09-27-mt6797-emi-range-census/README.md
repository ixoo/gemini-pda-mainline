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
