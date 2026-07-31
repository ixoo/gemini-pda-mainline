# DA921x OF-modalias isolation

| Field | Value |
| --- | --- |
| ID | `2026-07-30-da921x-of-modalias-isolation` |
| Device | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does the real `dlg,da9214-legacy` OF modalias uevent cause the
pre-serviceability reset?

The candidate preserves the exact real-compatible OF child, its resources,
the module-free initramfs, and the no-A72 serviceability baseline. One
experiment-only I2C-core branch omits only the OF modalias contribution for
that compatible and falls through to the already-exonerated I2C modalias.

## Decision

- Serviceability with the real OF node and I2C-only modalias implicates OF
  modalias generation or emission.
- Another reset after the suppression marker places the failure earlier in
  the real-compatible OF-node instantiation path.
- Absence of the exact config, binary branch, real OF child, or module-free
  initramfs invalidates the candidate.

## Safety

The option adds no driver or transfer path. The DA921x driver remains
module-only and its module and loader are absent from the initramfs. CPUs 8
and 9 remain offline. Runtime acceptance requires an unbound `0x68` client,
the real OF node, the I2C-only modalias, zero I2C/oracle counters, and the
complete existing serviceability baseline. No device partition is accessed
by the candidate.

## Status

The focused kernel built as `7.1.3-gemini-da921x-ofalias`. Its resolved config
enables the exact diagnostic, keeps the matching driver module-only, and keeps
A72 power disabled. The Image contains the suppression marker.

Two independent container assemblies were byte-identical. The raw candidate is
`78c2401f888d20683a2d65d7589e58676c78d65ba473ec751a62852afba70e4e`;
the exact 16 MiB boot2 image is
`5cc29e8db0f02988d2e66dc0976cf3e05e023fd3a93ae55ea3e67a54a9064db2`.
All 32 LK/container gates passed. Direct DT validation preserved the exact
enabled `dlg,da9214-legacy` child and `0x68,0x69` tuple. The exact module-free
initramfs contains neither the driver module nor `modprobe`.

The source-pinned candidate builder is
`b5562f03f3287d7eaafcadb5e1250f900cc279c9c5a4768843b33bbf52142e7f`.
The guarded no-new-backup installer is
`7b762d9c80bea54cf61584eaa7f2d5742e877ee00257c8d3b5ae8564e2bb5a64`.
The read-only runtime verifier is
`63c1e5ba22d33b55c47b7c6b04885772e3fc738eedbe3c31e6f2119e18051f85`.
See [offline validation](results/offline-validation.txt) and the
[pre-boot hypothesis](results/pre-boot-hypothesis.txt).

The guarded installer resolved logical `boot2` as `/dev/mmcblk0p30` while
Gemian boot ID `2221f126-925e-4670-8385-273f4790d363` was active. It confirmed
the exact name-only predecessor, wrote the padded candidate, synchronized and
flushed it, and required both an on-device full-partition checksum and an
independent 16 MiB byte comparison. Both matched
`5cc29e8db0f02988d2e66dc0976cf3e05e023fd3a93ae55ea3e67a54a9064db2`.
No new backup was created under the project policy. The temporary readback was
removed and shutdown was confirmed. See the
[installation result](results/install-boot2-20260730-2154.txt).

The experiment patch has actual author metadata but no DCO sign-off. It is an
experiment-only diagnostic and is not submission-ready.

## Runtime result

Attempt 1 was serviceable on `7.1.3-gemini-da921x-ofalias`, boot ID
`58fc7894-fe30-425d-95c0-9569084193a1`. The exact read-only verifier confirmed
the enabled real-compatible `1-0068` client, attached OF node, unbound state,
and one suppression marker. The client retained its OF-derived read-only
sysfs modalias, while its add-event used the I2C fallback. Every I2C6
transfer, DMA, start, IRQ, and oracle counter remained zero; sysfs remained
read-only and the complete serviceability baseline survived.

Native reboot returned Gemian `3.18.41+` on boot ID
`614a1303-771e-4602-a9a6-a6d4dea75021`. See the
[runtime result](results/runtime-attempt-1-20260730.txt).

This rules out real-compatible OF-node creation itself as sufficient. Combined
with the failing exact no-module candidate, the remaining boundary is adding
the real-compatible OF modalias to the I2C device's add-event environment.
