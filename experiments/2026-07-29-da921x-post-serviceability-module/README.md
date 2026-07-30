# DA921x post-serviceability module probe

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-29-da921x-post-serviceability-module` |
| Status | `installed and shut down; owner-attended boot pending` |
| Subsystem | regulator, I2C, arm64 Device Tree |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-07-29 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does an enabled legacy DA921x DT child remain serviceable when its
identification driver is not built into the kernel, and can loading that exact
driver once after serviceability safely perform the fourteen-read probe?

The profile preserves the Gate 3 patch stack, enabled child, I2C6 handoff,
read-only lifecycle oracle, CPU0--7 baseline, and CPU8/9 exclusion. Its
decision-changing kernel delta changes only
`CONFIG_REGULATOR_DA9213_LEGACY=y` to `m`, gives the diagnostic a distinct
kernel/USB identity, and packages the module in the serviceability initramfs
without any automatic loader reference.

## Safety assessment

Before the explicit module load, the enabled child may be instantiated but no
driver can probe it and every I2C6 transfer/oracle counter must remain zero.
The module contains the already-reviewed fixed fourteen-read identification
probe and no register-data write, provider, IRQ, PM, remove, shutdown, retry,
reset, or A72 path.

The module may be loaded exactly once only after kernel, USB, console,
keyboard, CPU, handoff, zero-counter, enabled-child, and unbound-client gates
pass. Any pre-load regression blocks the load. Any nonzero pre-load transfer
or write/other oracle counter rejects the candidate. The post-load result must
be either the exact fourteen-read identity match or a bounded failure prefix;
no retry is allowed.

## Decision

- A serviceable pre-load state proves that DT client creation alone is not the
  prior boot failure.
- A successful explicit module load with exact `14/8/6` read counters and all
  write/other counters zero localizes the prior failure to early automatic
  probe timing.
- A post-load watchdog or serviceability failure localizes the regression to
  the driver probe or its fourteen-read sequence independent of boot timing.
- A pre-load boot failure points to a kernel/configuration effect of changing
  the driver linkage and does not justify a load attempt.

No result permits a provider, writable regulator operation, or A72 request.

## Observations

The managed Linux 7.1.3 build reused the pinned prepared source and a distinct
out-of-tree build directory. The resulting kernel release is
`7.1.3-gemini-da921x-mod`; its packaged config hash is
`23f3affc7acb0e3ddda7ace6b51921225fd260d06eccb514e8547fadb0480964`.
The DA921x module has no loadable-module dependency, all fourteen of its
undefined imports resolve against the exact kernel’s built-in symbol table,
and its hash is
`fa8fa79cd7a198f8e3312c3dc251e3a9c64e741c7ae8201c12402eb25e96bffb`.

The deterministic initramfs builder preserved every Gate 3 member and added
only `lib/` plus the mode-`0400`
`lib/da9213-legacy-regulator.ko`. No inherited member names that path. Two
initramfs constructions and two Android boot-container assemblies matched.
All 32 LK gates passed. The unpadded candidate hash is
`b57766abae0bc330d911f1b108498c02b88995e73cdb663ee86b87b0998b46a1`;
the exact 16 MiB boot2 hash is
`86b0efaa2beafa97bd6382ec457508d0b516dab813d6ebbe8b1b7de1f4f88f17`.
See `results/offline-validation.txt`.

On Gemian boot ID `22741c5b-095f-4d7e-acee-67ee2859525c`, live GPT resolved
boot2 as `/dev/mmcblk0p30`, separate from root `/dev/mmcblk0p29`. The exact
probe-isolation predecessor matched, battery state was `100|Good`, and no new
partition backup was created. The write was synced and flushed; both the
on-device full checksum and an independent streamed 16 MiB readback matched.
The temporary staging and readback files were removed. The device then shut
down cleanly and became unreachable. See
`results/install-boot2-20260729.txt`.

## Runtime procedure

The owner selects `boot2` once. Runtime access is the USB netcat endpoint at
`10.15.19.82:2323`, not SSH. Before loading anything, record exact
serviceability, enabled-child/unbound-client state, handoff state, and every
I2C6/oracle counter. If and only if all pre-load gates pass and every counter
is zero, execute `/bin/busybox insmod
/lib/da9213-legacy-regulator.ko` exactly once. Do not retry.
