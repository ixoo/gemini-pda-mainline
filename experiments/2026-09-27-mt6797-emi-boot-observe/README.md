# Mainline inherited EMI policy observation

The accepted passive mainline owner has a checked-OFF CONN domain and a
probe-time VCN28 control sample. It has not read the EMI MPU regions covering
the boot-allocated CONSYS reservation. A carrier-up Gemian boot reported
regions 18 and 19 over its first MiB, while broad region 23 overlapped them.
That boot cannot show which protection survives the transition to mainline.

The named `mt6797-a53-emi-boot-observe` profile extends the exact device-tested
VCN28 observer by one diagnostic patch. After the existing OFF check, the owner
calls the MT6797 vendor-defined EMI MPU **read** service (`0x82000208`) for
the range and policy registers of regions 18, 19 and 23 and logs their six raw
32-bit values once. It does not call the SET or WRITE services, alter power,
reset, rail, remap or firmware state, or populate a WLAN child. The service ID
and register offsets were checked against pinned public vendor source revision
`c5b0be85017ad0c599725e8273842efdbecdd88a`: the
[`mt_secure_api.h`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_secure_api.h)
(SHA-256 `f810af34…a4b421`),
[`emi_reg_rw.c`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/emi_mpu/emi_reg_rw.c)
(SHA-256 `da41e7d3…375d858e0`) and
[`emi_mpu.h`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h)
(SHA-256 `a59c8a9a…a66ce2a5aed68d`). The implementation expresses only those
register and interface facts; it does not copy vendor code. The selected
source is a comparator, not yet byte-matched to the executing secure firmware.

## Decision for one boot

Hypothesis: a cold mainline boot has an attributable snapshot of the
EMI ranges and policies that apply to the CONSYS reservation before any WLAN
effect. The unique observation is three `EMI boot region=` records in a
complete authenticated kernel log, bound to the exact boot2 candidate and
changed boot ID. The collector must also preserve the A53 service regression
and confirm a changed-boot return to Gemian. A missing record, read-service
error signature or regression rejects the candidate. If regions 18/19 are
inherited with the expected ranges and policies, the owner can investigate
adoption without a protection write; if absent or different, it must design
the protection transaction before firmware execution. Region 23 is sampled in
either branch to expose the overlap premise. No branch proves master/domain
routing, overlap arbitration or exclusive writer handoff, and none authorizes
an active CONN or Wi-Fi transition alone.

The build must come from a clean pushed commit through Buildbox. Only a
validated candidate may be installed in logical boot2 through the reviewed
live-GPT guard and full-partition readback. The owner selects boot2 physically
after a finite USB collector is armed. Full logs, firmware and credentials
remain private; publish only sanitized values and evidence checksums.

The internal patch has synthetic non-certifying authorship and is not an
upstream submission.
