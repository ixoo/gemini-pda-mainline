# LK-repaired read-only provider design

## Fixed predecessor

The exact positive predecessor is the 2026-08-17 LK CPU-clock iterator repair.
It fixes the kernel, initramfs, Android-v0 addresses, peripheral-only USB path,
I2C5/AW9523/polling keyboard, watchdog takeover, CPUs 0-7 online, CPUs 8-9
offline, and native reboot behavior.

## Source delta

The kernel-built Gemini DT receives exactly these properties:

| CPU nodes | `clock-frequency` |
| --- | ---: |
| `cpu@0` through `cpu@3` | 1,391,000,000 |
| `cpu@100` through `cpu@103` | 1,950,000,000 |
| `cpu@200` and `cpu@201` | 2,288,000,000 |

No node status, compatible, enable method, CPU operation, or clock consumer is
changed.

## Configuration delta

The new profile extends `da921x-modules-arm64-entry-ledger` with:

- `CONFIG_NVMEM=y`;
- `CONFIG_NVMEM_MTK_ATAG_DEVINFO=y`;
- `CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y`;
- the observer KUnit runtime gate explicitly disabled; and
- one unique local version.

The existing entry ledger is retained so this candidate changes no already
proven early-entry instrumentation. Its retained-RAM records are not provider
evidence.

## Closure

- no regulator consumer or supply phandle;
- no writable regulator operation;
- no DA921x register-data write helper;
- no A72 provider owner;
- no CPU8/CPU9 request;
- existing I2C6 access-controller remains mandatory;
- LK-devinfo NVMEM is read-only and does not access efuse MMIO;
- `maxcpus=8` and the A72 initcall blacklist remain fixed.

## Runtime decision map

| Observation | Classification | Next action |
| --- | --- | --- |
| Exact kernel/DT; handoff and I2C6 ready; one DA921x bound record with `14/2/4/4/0`; internally consistent buck states; full serviceability; native reboot | `success-read-only-provider` | Publish runtime evidence and open only Roadmap gate 6 review. |
| LK-devinfo missing/malformed, handoff denied, I2C6 deferred, identity mismatch, provider-read failure, or no unique record while the kernel stays serviceable | `provider-prerequisite-or-read-failure` | Stop candidate and localize the reported stage; do not write or admit CPUs. |
| Any nonzero register-data-write count, setter/consumer/owner activity, or CPU8/CPU9 online/request | `safety-rejection` | Stop immediately; no repeat and no bounded-write gate. |
| No exact mainline identity before changed Gemian return | `pre-transport-inconclusive` | Recover retained evidence once; screen state is not an oracle. |
| Kernel fault or automatic reboot after exact identity | `runtime-failure` | Recover exact evidence and stop; do not infer provider cause without attribution. |
