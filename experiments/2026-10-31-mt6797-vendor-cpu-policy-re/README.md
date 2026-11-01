# Experiment: MT6797 vendor CPU policy and PCM/iDVFS reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-mt6797-vendor-cpu-policy-re` |
| Status | `completed` for the offline source and firmware study; runtime policy trajectory and external iDVFS trigger remain open |
| Subsystem | MT6797 PPM/HICA frequency policy, HPS activation, CPUHVFS PCM, ATF BigiDVFS/iDVFS |
| Device variant | Planet Computers Gemini PDA, MT6797X, Gemian 3.18 vendor stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | CPU cluster/OPP documentation and the A72 default-integration gate |

## Question or hypothesis

Can offline source and retained-firmware analysis resolve:

1. how PPM/HICA selects the frequency policy and per-cluster limits;
2. which writer owns each CPU cluster frequency/voltage transition, especially
   the Cortex-A72 split between the CSPM PCM and secure iDVFS; and
3. which parts still need live, read-only observation?

The hypothesis was that the policy and register-ownership mechanisms are
recoverable offline, while the runtime trajectory and the external iDVFS
enable/disable actor are not.

## Provenance and environment

- Public vendor source: Gemian `gemini-linux-kernel-3.18` commit
  `59e00a9144d782e148332009a835b99c43382467` (chosen observer/source
  equivalent; the active private Gemian build is separate).
- Key source hashes at that revision:

  | File | SHA-256 |
  | --- | --- |
  | `ppm_v1/src/mt_ppm_main.c` | `b551d08b8b10b48e8cde7e49c211b2d5133b65d7c2b6540f948c4bbb1b229e00` |
  | `ppm_v1/src/mt_ppm_policy_hica.c` | `76a2b2631ea07c4be0182ed77e5705a878050e4bb5c2d9ffd4a9b96ea956ec57` |
  | `ppm_v1/src/mach/mt6797/mt_ppm_power_state.c` | `fa458fa11508091568d6a4eb44c554618d01cc0b3a325800ff441c7afcbd5594` |
  | `ppm_v1/src/mach/mt6797/mt_ppm_platform.h` | `6d1b1a18bcfc0d85eb8c1b6b7608fba884d8b3e840a82926d07c130ca784033b` |
  | `mt6797/mt_cpufreq.c` | `3f69c3b3a331a70336f7a4010cd4482f6743b0b69cef6df4c641d5be259eccd3` |
  | `mt6797/mt_cpufreq_hybrid.c` | `2aeab8496b9ba7a107e380ff211fe7f08d76e69ad63ece7f0e099762dcf50712` |
  | `mt6797/mt_cpufreq_hybrid_fw.h` | `4b89d935857393f650e7c439333d37f95e4424c3645795c5e31e6ae7c046a4a5` |
  | `mt6797/mt_idvfs.c` | `7232f5ba7347511d97da6947c6833811b439d3116f95a13e631be40d7033b2e7` |
  | `mt6797/mt_hotplug_strategy_algo.c` | `1100eac008d27a9bab9bba3a445aa8b7d51d602e15146b0990bc759c7d7c7f09` |
  | `mt6797/mt_hotplug_strategy_cpu.c` | `394bcc4569e540000bacb58800e61156734186c2d3d0247435bf7e0ac1033127` |
  | `mt6797/mt_hotplug_strategy_core.c` | `d8ba0dfda736c7d54439eabbbd30d85037f6b182822fed2ec931046bc68bb747` |
  | `mt6797/mt_hotplug_strategy_ops_mt6797.c` | `a536ff2f1702101d332c50b32d475509a65ebb93c4ce7cf7587a5c3a36c9d476` |

- Retained private firmware: preloader, LK, TEE/ATF and SCP partition images.
  The TEE payload hash and build identity are already recorded in the
  [A72 firmware/power contract](../2026-07-22-a72-firmware-power-contract/README.md).
  No firmware bytes or disassembly are copied into Git.
- Runtime cross-check: retained Gemian dmesg and the
  [CPU/scheduler policy capture](../2026-07-21-gemian-cpu-scheduler-policy/README.md).
- Mainline comparison: `docs/hardware/mt6797-cpu-clusters.md`.

## Safety assessment

Entirely offline and read-only. No device, boot candidate, partition, module,
CPU mask, frequency, voltage or firmware was accessed or changed. Private
firmware stayed in the reverse-engineering workspace; only independently
written conclusions, source paths, hashes and short generic strings are
recorded here.

## Method

1. Reconstruct the PPM v1 policy order, state limits and HICA transition rules
   from the pinned source, including constants in
   `mt_ppm_platform.h`.
2. Trace how PPM limits reach cpufreq and HPS through their registered
   callbacks, and how HPS converts per-cluster core limits into
   `cpu_up()`/`cpu_down()`.
3. Identify the compiled CPUHVFS PCM variant from the header guard and decode
   the retained PCM instruction array: function boundaries, event/status
   registers, register windows written, and the B-cluster path.
4. Correlate the PCM path with the ATF BigiDVFS SMC handlers and the iDVFS
   driver, then with the live dmesg ordering of iDVFS enable/disable and
   cluster2 on/off.
5. Record what is proved by static evidence, what is inferred from the live
   log, and what remains runtime-only.

## Findings

- [PPM/HICA policy model](results/ppm-hica-model.md): exact state limits,
  transition thresholds, hold counts, policy aggregation, and the
  cpufreq/HPS callback split.
- [PCM and iDVFS ownership](results/pcm-idvfs-ownership.md): the live PCM is
  the `v0.1` software-request image; it sequences OPP-level frequency and
  coarse voltage for all four domains. Secure iDVFS is a B-cluster closed-loop
  layer enabled just before cluster2 on and disabled just after cluster2 off.
  The iDVFS enable/disable caller is not in the inspected kernel call path.
- [Offline boundary](results/offline-boundary.md): the preloader and A53
  CPUSYS0/1 pass was bounded but not fully decoded; the exact reasons and the
  remaining evidence are recorded.
- [Gemian userspace candidates](results/userspace-candidates.md): the selected
  vendor corpus contains PPM/HPS/thermal policy clients but no iDVFS trigger.
  `libperfservice` is the main userspace CPU-policy actor; the thermal stack is
  indirect; `power.mt6797.so` only controls rush boost and FPS bound.

## Limits

- Static source proves the mechanism, not the runtime trajectory. The exact
  sequence of HICA states under a given workload still needs a read-only
  trace.
- The PCM decode proves which registers the image can write; it does not prove
  which writes actually occur on every transition.
- The PCM/iDVFS split is resolved at the layer level but not to a
  cycle-accurate arbitration rule. Both mechanisms can act on the B cluster.
- The external iDVFS enable/disable trigger is not identified. In-tree call
  sites are `#if 0`; the live dmesg ordering suggests a userspace or
  vendor-service actor.
- The preloader's exact CPU/PLL register sequence and the A53 CPUSYS0/1
  MTCMOS sequence were not fully decoded in this pass. The retained binaries
  and strings bound the behavior, but no per-register sequence is claimed.
- No physical voltage measurement, cold-boot repeatability or write-safety
  result follows from this experiment.

## Follow-up

1. One bounded read-only session to sample `/proc/ppm`, `/proc/hps`,
   cpufreq state and `/proc/idvfs` under a controlled workload, to close the
   runtime trajectory and identify the iDVFS trigger.
2. A focused ATF pass for the A53 CPUSYS0/1 path if that detail becomes
   decision-relevant.
3. Keep all write/rollback, thermal and physical-rail claims behind their own
   admitted experiments.

## Evidence index

- [PPM/HICA policy model](results/ppm-hica-model.md)
- [PCM and iDVFS ownership](results/pcm-idvfs-ownership.md)
- [Offline boundary](results/offline-boundary.md)
- [Gemian userspace candidates](results/userspace-candidates.md)
- [Gemian CPU/scheduler policy](../2026-07-21-gemian-cpu-scheduler-policy/README.md)
- [A72 firmware/power contract](../2026-07-22-a72-firmware-power-contract/README.md)
- [Secure CPU-off attribution](../2026-08-05-a72-secure-cpu-off-attribution/README.md)
- [CPU clusters hardware record](../../docs/hardware/mt6797-cpu-clusters.md)
