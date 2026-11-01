# Gemian userspace candidates for CPU policy

Inputs:

- The owner-authorized 721-entry vendor/bridge corpus extracted from the
  installed Gemian system (`artifacts/device-userspace/gemian-2019`, private).
- The public Planet Android device tree
  `planet-community/android_device_planetcom_geminipda`, commit
  `8f7cd432feb3252497497a5259c7e4e326407a4f`.
- Existing ELF audits in [vendor userspace](../../../docs/hardware/vendor-userspace.md)
  and [thermal management](../../2026-10-31-mt6797-thermal-management/README.md).

This is a static string/interface audit. No vendor binary was executed.

## Candidates

| Component | Hash / path | Kernel interfaces | Relevance |
| --- | --- | --- | --- |
| `libperfservice.so` (64/32) | `ae225a44…` / `740d62ba…` | `/proc/ppm/mode`, `/proc/ppm/policy/userlimit_*`, `/proc/ppm/policy/perfserv_*`, `/proc/hps/num_base_perf_serv`, `/proc/hps/num_limit_power_serv`, `/proc/perfmgr/boost/*`, `/dev/cpuctl/tasks`, `/sys/devices/system/cpu/cpufreq/hotplug/cpu_num_base` | Main userspace CPU policy client: PPM mode, per-cluster min/max core/frequency, cpuset boosts |
| `libperfservicenative.so` (64/32) | `8b232b9c…` / `90ab2487…` | none directly | Client API for the performance-scenario service |
| `thermal_manager` | `00898904…` | Loads `/vendor/etc/.tp/thermal.conf`, writes `/proc/driver/thermal/tz*` and `/proc/mtkcooler/*` | Thermal policy/cooler binding; indirect PPM budget |
| `libthermalalgo.so` | `54a4c4ed…` | netlink thermal source, `libthermal_algo_setup` | Adaptive thermal algorithm |
| `thermalloadalgod` | `cb3461b1…` | loads `libthermalalgo.so` | Load-based thermal budget daemon |
| `thermalindicator` | `f070dd7c…` | reads `/proc/ttpct` | Read-only throttling indicator |
| `thermal` | `541ffc54…` | `/proc/driver/thermal/*`, network operstate, CCCI | Modem/network thermal reporting |
| `power.mt6797.so` | existing audit | `/proc/hps/rush_boost_enabled`, `/d/ged/hal/fps_upper_bound` | Only rush-boost and FPS bound; no CPU frequency/core control |
| `repowerd` | `6c206722…` | display/suspend DBus; Ubuntu performance-booster scenarios | Interactive boost path; no direct cpufreq writes found |
| `perf_native_test` | - | same perfservice API | Test tool, not policy |

## On-device policy files

These are the files that actually determine the vendor CPU policy at runtime.

### `vendor/etc/perfservscntbl.txt`

This is the main scenario policy for `libperfservice`. It sets minimum cores,
minimum frequencies, HPS thresholds, root cluster, PPM big-cluster limit and
VCORE for named scenarios:

| Scenario | Policy |
| --- | --- |
| `SCN_APP_TOUCH` | min 3 cores, 1.287 GHz |
| `SCN_SW_FRAME_UPDATE` | min 3 cores, 1.287 GHz; HPS up 80, down 65 |
| `SCN_APP_SWITCH` | cluster0 0 cores / 2.0 GHz; cluster1 4 cores / 2.5 GHz; cluster2 3.0 GHz; VCORE 3; PPM big limit 0 |
| `SCN_PACKAGE_SWITCH` | cluster0 0 / 2.0 GHz; cluster1 4 / 2.5 GHz; cluster2 2 cores / 3.0 GHz; VCORE 3; PPM big limit 0 |
| `SCN_PROCESS_CREATE` | same as package switch |
| `SCN_GAME_LAUNCH` | same as package switch |
| `SCN_APP_ROTATE` | cluster0 0 / 2.0 GHz; cluster1 4 / 2.5 GHz; VCORE 3 |
| `SCN_GALLERY_BOOST` | cluster0 0 / 2.0 GHz; cluster1 2 / 2.5 GHz; cluster2 2 / 3.0 GHz; PPM big limit 0 |
| `SCN_GAMING` | VCORE 1; rush boost off; heavy-task off; HPS up 80/down 70; root cluster 0; cluster2 max cores 0 |

The 3.0 GHz and 2.5 GHz values exceed the live B and L tables; they are
requests that PPM clamps to the available OPPs. The cluster2-max-zero gaming
entry explicitly disables the A72 cluster for that scenario.

### `vendor/etc/perfservapplist.txt`

Only one per-app rule is shipped:

```text
CMD_SET_CPU_CORE_MIN com.imangi.templerun2 3
```

### `vendor/etc/.tp/thermal.conf`

The CPU-relevant records are:

| Path | Value | Effect |
| --- | --- | --- |
| `/proc/driver/thermal/tzcpu` | `3 110000 0 mtktscpu-sysrst 58000 0 cpu_adaptive_0 57000 0 cpu_adaptive_1 ...` | 110 °C reset, 58/57 °C adaptive coolers |
| `/proc/mtkcooler/cpu_adaptive_0` | `EXIT 6000` | Adaptive CPU power-budget cooler |
| `/proc/mtkcooler/cpu_adaptive_1` | `mtktsAP 66000 EXIT 5000` | Board-temperature adaptive cooler |
| `/proc/mtkcooler/...` | various | Other domain coolers; no direct cpufreq write |

The thermal layer produces cooler actions and PPM power budgets, not direct
frequency writes. The `.thermal_policy_00..03`, `thermal.off.conf` and
`.ht120.mtc` files are alternative policy sets; they change trips/coolers, not
the CPU OPP mechanism.

### `init.mt6797.rc`

The normal boot cpuset policy is:

```text
/d/cpuset/foreground/cpus          0,2-9
/d/cpuset/foreground/boost/cpus    0,2-9
/d/cpuset/background/cpus          0,2-3
/d/cpuset/system-background/cpus   0,2-7
/d/cpuset/top-app/cpus             0-9
```

The same file owns the `/proc/hps/*`, `/proc/ppm/*` and `/proc/cpufreq/*`
permissions but **does not write policy values**. HPS/PPM therefore start from
their kernel defaults. It also starts `thermalloadalgod`, `thermal_manager`,
`thermal`, `thermald` and `thermalindicator`.

`meta_init.project.rc` and `factory_init.project.rc` are the exception: they
disable HPS (`write /proc/hps/enabled 0`) and force only CPU0-1 online, with
CPU2-9 offline. Those are meta/factory modes, not normal boot.

### Boot command line

The LK/Gemian boot command line contains `maxcpus=5`. This is the initial cap;
HPS can later bring additional CPUs online up to the possible/present mask.

## What the userspace layer actually does

`libperfservice` is the clearest contributor. Its strings and exported API
show that it:

- switches PPM between `Performance`, `Just_Make` and `Low_Power`;
- writes per-cluster `userlimit_min_cpu_core`, `userlimit_max_cpu_core`,
  `userlimit_min_cpu_freq` and `userlimit_max_cpu_freq`;
- sets the HPS performance-service core limits and `cpu_num_base`;
- moves selected tasks into `/dev/cpuctl/tasks` and uses the
  `/proc/perfmgr/boost` cpuset interface;
- can request a PPM `perfserv_perf_idx`, GPU frequency levels and a "vcore"
  level.

It is a **policy client**, not a governor. It constrains PPM/HPS and can pin or
boost a process; the kernel still performs the OPP and hotplug transitions.
A mainline system should not port this ABI. The useful facts are the vendor
control surfaces and the fact that a userspace actor can override PPM/HPS
limits at runtime.

`thermal_manager` and its algorithm are a separate thermal-policy stack. They
write zone trips and cooler parameters, which ultimately feed the kernel's PPM
thermal budget. They do not write CPU PLL/regulator registers and do not
mention iDVFS.

`power.mt6797.so` is only a rush-boost/FPS-bound shim, matching the earlier ELF
audit. `repowerd` has performance-booster scenario calls, but no direct
cpufreq/PPM path was found in its strings; it likely reaches the vendor stack
through libhybris/hardware booster on interactive transitions.

## The iDVFS trigger is not in this corpus

No selected file contains `idvfs`, `dvt_test`, `/proc/idvfs`, or a direct write
to the iDVFS proc interface. The public device-tree init rules also contain no
iDVFS entry. The kernel call sites are `#if 0`, and `mt_idvfs.c` does not start
a thread or register a CPU notifier.

Therefore the live iDVFS enable/disable trigger is still unidentified. It is
not any of the audited power/thermal/perf binaries. Possible remaining
locations:

- a vendor binary or init script not selected into the 721-file corpus;
- a policy module loaded by `/vendor/etc/.tp/thermal.conf`;
- a native Gemian service or boot script outside the selected Android tree;
- a userspace diagnostic/test tool invoked by the vendor image.

This cannot be closed from the selected corpus. It needs a read-only process
and `/etc`/`/usr` inspection on a running Gemian system, ideally correlated
with one natural cluster2 on/off event.

## Mainline relevance

- Do not port `libperfservice`; its PPM/HPS proc ABI is vendor policy.
- Expect userspace to constrain PPM/HPS in the vendor stack, so a mainline
  cpufreq/thermal implementation must define its own policy boundary.
- The thermal `.tp` layer is data-driven zone/cooler configuration, not a CPU
  driver; mainline should use standard thermal zones and cooling devices.
- No audited userspace component provides a missing CPU clock/regulator
  provider. The mainline provider work remains kernel-side.
