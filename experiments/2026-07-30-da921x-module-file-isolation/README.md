# DA921x real-compatible module-file isolation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-30-da921x-module-file-isolation` |
| Status | `attempt 1 failed before serviceability; module availability exonerated` |
| Subsystem | regulator, I2C, arm64 Device Tree, module loading |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-07-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Did the failed real-compatible module-profile boot depend on the manual-only
module file being present, despite the absence of an automatic invocation
path?

The candidate restores exact enabled DT compatible `dlg,da9214-legacy` and
preserves the exact module-profile kernel, configuration, DT resource
contract, Android header, and LK placement. It replaces the module-bearing
initramfs with the exact Gate 3 initramfs, which contains no DA921x module,
`modprobe`, `insmod` invocation, or module reference.

## Decision

- Serviceability would expose an unexpected dependency on module-file
  availability before the declared manual load.
- Another pre-serviceability failure would place the boundary before module
  availability and keep compatible-specific kernel/DT handling in scope.
- No module can be present or loaded. Neither result permits provider or A72
  work.

## Safety

The candidate contains no DA921x module and cannot execute the identification
driver. Runtime collection is read-only and must not bind a driver, trigger an
I2C transfer, or access a device partition.

## Observations

The source-pinned assembly produced raw candidate
`539f6c35e368d99d2c348c48d9de551dd88d28d00d37a28cf6372cd158519d89`
and exact 16 MiB boot2 image
`f89eb0ed2608a9e6a90ad939686c06d26d7420ae2c29854ada6a836fac823377`.
All 32 LK/container gates passed. Direct inventory confirmed that the exact
Gate 3 initramfs has no DA921x, module-index, or module-loader reference.
Direct DT inspection confirmed enabled `dlg,da9214-legacy` with the unchanged
`0x68,0x69` tuple.

See [offline validation](results/offline-validation.txt) and the
[pre-boot hypothesis](results/pre-boot-hypothesis.txt).

The guarded installer resolved logical `boot2` as `/dev/mmcblk0p30` from the
live GPT while Gemian boot ID
`189deafa-09eb-4395-a88b-e77868741fbf` was active. The exact unmatched-client
predecessor checksum matched. It wrote the padded candidate, synchronized and
flushed it, then required both a matching on-device full-partition checksum
and an independent 16 MiB byte comparison. Both matched
`f89eb0ed2608a9e6a90ad939686c06d26d7420ae2c29854ada6a836fac823377`.
No new backup was created under the project’s standing backup policy. The
temporary readback was removed and device shutdown was confirmed. See
[installation result](results/install-boot2-20260730-2011.txt).

## Attempt 1

The owner selected `boot2` once and observed a white screen followed by an
automatic reboot. No candidate console or USB/netcat serviceability was
observed. Gemian returned as `3.18.41+` on new boot ID
`b04cd6b0-f10f-4ff2-9cdd-c1d2b66ffc63`. A full read-only checksum of
live-GPT-resolved `/dev/mmcblk0p30` still matched the exact candidate
`f89eb0ed2608a9e6a90ad939686c06d26d7420ae2c29854ada6a836fac823377`.

The read-only recovery capture found the ramoops geometry intact but no pstore
members. It did not modify or remove pstore records. See
[runtime result](results/runtime-candidate-no-module-attempt-1-20260730.txt).

## Conclusion

Attempt 1 fails before serviceability with the DA921x module file absent from
the exact initramfs and no loader path. Module availability, module loading,
and driver execution are therefore outside the causal boundary. Combined with
the serviceable unmatched-compatible run, the failure is specific to the real
compatible path before any DA921x driver code can execute.

The exact kernel Image contains no `dlg,da9214-legacy` string or resident match
table; the driver is configured only as a module, `CONFIG_UEVENT_HELPER` is
disabled, and the module-free initramfs has no listener or loader. Exact-source
inspection leaves the compatible-derived I2C client name and OF modalias
uevent as the early string-dependent paths. See the
[source-path audit](results/compatible-path-audit.txt).

The next discriminator must boot serviceably with the DT child disabled and
module absent, then create one unbound name-only `da9214-legacy` I2C client
after all zero-transfer gates pass. That distinguishes the compatible-derived
client name from the OF-node/modalias path while adding a post-serviceability
observation boundary. This exact failed candidate must not be repeated.
