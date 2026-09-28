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

## Built candidate

Clean pushed commit `35465d47` built the 544 selected patches on Buildbox. The
complete package inventory passed validation, with image and config identities
in the [build receipt](results/build.json). Strict Checkpatch found no source
warning or check; the intentionally absent synthetic DCO sign-off remains an
error for upstream submission. The [candidate builder](build-candidate.py)
verified the package, reused the exact boot-tested VCN28 DTB, initramfs and
config, and replaced only `Image.gz`. The Android LK container and exact 16 MiB
padding passed validation. The [candidate receipt](results/candidate.json)
pins full boot2 SHA-256
`0f2bb23cda82e8b119a823a4ffa68d6b60b0bd9399f592b5ee4d9db1909c7710`.
No device action is implied by the build or candidate validation.

The [installer wrapper](install-passive.py) checks that the current logical
boot2 predecessor is the VCN28 image and uses the reviewed live-GPT device
guard and full-partition readback. The [host collector](passive-host.py) requires
the existing passive owner/VCN28 evidence, exactly one record for each of EMI
regions 18, 19 and 23, a complete sealed log, the A53 regression and one
modern CONN provider. The finite [USB watcher](watch-boot.py) waits for the
owner's physical boot2 selection after installation and clean shutdown.

The [deployment receipt](results/deployment.json) records live-GPT `boot2`
resolution, inactive root, stable power, exact predecessor, guarded write,
matching full-partition readback and clean Gemian shutdown. The private
installer and full deployment summary are pinned by checksums in that receipt.
Collector and USB-watcher offline preflights passed; the physical boot2 result
is separate.

## Device result and decision

The owner selected boot2 once after the 900-second USB watcher was armed. The
authenticated changed-boot mainline session bound one modern CONN provider and
one passive owner, retained VCN28 `0x1a60`, and logged exactly three EMI
records. Every region-18, -19 and -23 range and policy read returned zero. The
1,849-record kernel log sealed completely and the A53 service regression
passed. The collector requested the reviewed native return only after sealing
the evidence and confirmed a changed Gemian boot.

In that returned Gemian boot, a bounded read of the existing EMI sysfs report
found region 18 over `0xbfa00000..0xbfa7ffff`, region 19 over
`0xbfa80000..0xbfafffff`, and broad region 23 over
`0x00000000..0xffffffff`. The boot ID was stable around that read and `wlan0`
had carrier. This positive control supports the conclusion that the Gemian
policy is not visible to mainline at the owner's probe; it is not proof that
every underlying register is zero, because the selected vendor SMC source is
not byte-matched to the executing secure firmware. The two observations are in
different boots.

The sanitized [runtime receipt](results/runtime-1.json) pins the read values,
candidate, boot identities, complete-log hash and returned-Gemian control. The
complete logs and sysfs response remain ignored private evidence. The next
owner cannot assume inherited region-18/19 protection. It needs an explicit
owned protection transaction, plus master-domain/overlap validation, before
firmware execution. This read-only test did not authorize an active transition.
