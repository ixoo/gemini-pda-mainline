# CPUHVFS PCM and secure iDVFS ownership

Sources: the public Gemian `59e00a91` source, the retained CPUHVFS PCM image
embedded in `mt_cpufreq_hybrid_fw.h`, the retained TEE/ATF payload, and the
retained Gemian dmesg. The PCM instruction indices below are positions in the
2025-instruction `v0.1` array and are reproducible from the public header.

## 1. Which PCM image is built

`drivers/misc/mediatek/base/power/include/mt_cpufreq_hybrid.h` leaves
`CPUHVFS_HW_GOVERNOR` commented out. Therefore the built image is:

| Field | Value |
| --- | --- |
| Version | `pcm_dvfs_v0.1_160131_02` |
| Instructions | 2025 |
| Session | 2 |
| Mode | software-request, not hardware governor |

The live `/proc/cpufreq/enable_hw_gov` reports `0` and
`enable_cpuhvfs` reports `1`, which is consistent with the software-request
image being active. The exact private Gemian build is a separate artifact, but
its observer-relevant source lineage matches this variant.

## 2. Where the PCM runs and what it can reach

The kernel copies the image into 12 KiB CSRAM at `0x0012a000`, kicks the CSPM
PCM engine, and services it through the CSPM window at `0x11015000`. The
instruction array contains immediate accesses to:

| Window | Example addresses | Use |
| --- | --- | --- |
| CSPM/DVFSP | `0x110153xx`-`0x110158xx` | request/status, semaphores, event/control |
| MCUMIXED | `0x1001a270`, `0x1001a274` | A53/CCI mux and divider |
| MCUCFG2 | `0x10222470`, `0x10222498`, `0x102224c0`, `0x102224c8` | B-cluster control, PCW, monitor |
| PWRAP | `0x1100e000`-`0x1100e06c` | PMIC/DA9214 transactions |
| INFRACFG AO | `0x10001f9c`, `0x10001fa0` | VSRAM_L LDO |
| CSRAM | `0x0012a3xx` | PCM scratch/status |

This is enough to show that the PCM is the OPP-level sequencer for all four
domains, not just LL/L/CCI. It writes the A53/CCI clock fields, the B control
and PCW fields, the PMIC path, and the L-side SRAM LDO.

## 3. B-cluster path in the PCM

The concentrated B path is instruction range `0x5c9`-`0x62e`:

- `0x5c9` calls a helper, then reads B monitor `0x102224c8`.
- `0x5ee`-`0x5fa` writes B control `0x10222470`.
- `0x60a`-`0x60f` writes B PCW `0x10222498` and mirrors the value to CSRAM
  `0x0012a3a4`.
- `0x619`-`0x620` writes `0x102224c0` with one of two constants.
- `0x621`-`0x62c` completes the `0x10222470` update and calls a helper.

The PCM does not write the ATF-only PLL enable/post-divider register
`0x102224a0` or the SRAM selector `0x102222b0` in this path. Those are reached
through the secure BigiDVFS services instead. This is a real division:

- PCM writes the B PCW/control/monitor interface.
- ATF owns the B PLL enable/post-divider and the secure SRAM-LDO selector.

## 4. ATF BigiDVFS services

The retained TEE payload implements the services already documented in the
[A72 firmware/power contract](../../2026-07-22-a72-firmware-power-contract/README.md):

| FID | Handler | Role |
| --- | --- | --- |
| `0xc20003b0` | `0x105eb0` | BigiDVFS enable |
| `0xc20003b1` | `0x105ffc` | BigiDVFS disable |
| `0xc20003b8` | `0x106450` | B PLL frequency/post-divider |
| `0xc20003bf` | `0x1065dc` | SRAM-LDO set |
| `0xc20003c1` | `0x1062d0` | software-request handshake |
| `0xc200035f` | read | whitelisted `0x1022xxxx` read |

ATF also owns PSCI `CPU_ON`/`CPU_OFF`, MP2 cluster/core MTCMOS, initial B
PLL/mux/divider and CCI snoop admission. It is not a Linux CCF provider.

## 5. The AP-side iDVFS driver

`mt_idvfs.c` prepares an I2C6 clock, initializes the iDVFS APB and writes a
DA9214 slave address of `0xd0`. On enable it:

1. reads the current BUCKB VSEL and `0x5e` enable state;
2. sets the secure SRAM LDO to 1.2 V;
3. enables iDVFS with `Fmax = 2900 MHz`, `Fcur = 750 MHz`, the current Vproc
   and 1.2 V Vsram;
4. runs the software-request/closed-loop path and logs the current B
   frequency percentage.

On disable it forces 30% / 750 MHz, disables the OTP channel, restores the
SRAM LDO to 1.1 V, and disables the secure service.

This is explicitly a B-cluster voltage/frequency loop, not a general CPU
policy. It uses DA9214 BUCKB (VPROC2) and VSRAM_B, and it is the mechanism
behind the observed `SRAM LDO setting = 120000` and `Vproc = 100000` messages.

## 6. Live ordering

The retained dmesg shows a repeatable order around the first B-cluster cycle:

| Time | Event |
| --- | --- |
| 2.1656 | iDVFS start enable, PTP1 ready, SRAM LDO 1.2 V, `Vproc = 100000`, `Fmax = 2900`, `Fcur = 750` |
| 2.1723 | `[CPUHVFS] cluster2 on` |
| 2.3324 | `[CPUHVFS] cluster2 off` |
| 2.3337 | iDVFS start disable, force 750 MHz, SRAM LDO 1.1 V, disable success |

The same pattern repeats for later cluster2 on/off cycles. This establishes
that iDVFS is brought up immediately before the B cluster is admitted and
torn down immediately after it leaves.

## 7. Who calls iDVFS enable/disable

This is the unresolved part. The inspected kernel source has:

- `BigiDVFSEnable_hp()` and `BigiDVFSDisable_hp()` call sites in
  `mt_cpufreq.c` inside `#if 0` blocks;
- no CPU notifier, workqueue or kthread in `mt_idvfs.c` that calls them;
- a writable `/proc/idvfs/dvt_test` interface, which can invoke enable,
  disable, manual frequency and channel controls.

The live ordering is therefore consistent with an external actor writing
`/proc/idvfs/dvt_test`, but the actor is not identified. It could be a vendor
userspace service, an Android/Gemian init script, or a thermal/power daemon.
This must be resolved by read-only userspace/process inspection, not by
kernel-source analysis.

## 8. Ownership model

| Layer | Owns | Confidence |
| --- | --- | --- |
| HPS | Core online/offline requests and per-cluster target counts | `confirmed` source + live |
| PPM/HICA | Per-cluster OPP/core limits and preferred cluster state | `confirmed` source + live dump |
| CPUHVFS PCM | OPP-level sequencing for LL/L/B/CCI; A53/CCI clock fields, B PCW/control, PMIC and VSRAM_L writes | `confirmed` static image + live status |
| ATF BigiDVFS | B PLL enable/post-divider, secure SRAM selector, enable/disable/SWREQ | `confirmed` prior static audit |
| AP iDVFS driver | B closed-loop voltage/frequency adaptation while B is online | `observed` source + live dmesg |
| External proc actor | iDVFS enable/disable trigger | `inferred`, identity unknown |

The important correction to the earlier "PCM vs iDVFS" question is that they
are not alternative owners of the same operation. They are layered:

```
PPM limits
   -> CPUHVFS PCM: choose OPP, sequence frequency and coarse voltage
       -> ATF BigiDVFS: set B PLL/SRAM secure state when requested
       -> iDVFS: adapt B voltage while the cluster is online
```

That model explains why both the PCM status and iDVFS logs change around a B
transition, without either being a duplicate implementation.

## 9. Remaining boundary

Not proved:

- the exact arbitration when PCM and iDVFS both touch the B PLL/rail in the
  same transition;
- the identity of the external iDVFS trigger;
- whether the private Gemian build contains the exact same PCM array as the
  public `59e00a91` source (the image is from the same lineage, but the active
  private build is separate);
- any cycle-accurate ordering inside a transition.

Those need a bounded read-only trace of PCM status, iDVFS registers, BUCKB,
SRAM-LDO and the calling process.
