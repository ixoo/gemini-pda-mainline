# Experiment: current mainline module and built-in closure

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-14-mainline-module-closure-audit` |
| Status | `completed` for package metadata; runtime module loading remains untested |
| Scope | Linux 7.1.3 Gemini package, first-boot and deferred consumer availability |
| Device variant | Gemini PDA board DTB, exact retail sub-variant not independently established |
| Safety | Package-only; no module was loaded and no hardware state was changed |

## Question

Which important Gemini consumers are built into the kernel, which are optional
modules, and what packaged module dependencies must a future root filesystem or
initramfs provide? A `.ko` existing in the package proves only that it was
compiled; it does not prove that the module can be loaded during early boot.

## Method

The audit reads the authoritative package metadata (`kernel.config`,
`System.map`, `modules.builtin`, `modules.dep`, and packaged `.ko` files). It resolves
only module-to-module edges present in `modules.dep`; dependencies satisfied
by built-in symbols, firmware, DT nodes, regulators, clocks, or userspace are
intentionally outside this closure. Every module hash is recorded so a later
rootfs assembly can be tied to the exact package.

Run it in the prepared VM:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2d9eea95daa \
   experiments/2026-07-14-mainline-module-closure-audit/scripts/audit-module-closure.sh'
```

The reproducible result for the current package is
[`results/module-closure-current-72-20260714.txt`](results/module-closure-current-72-20260714.txt).
The focused packet-semantics rebuild is reconciled against the prior package by
[`scripts/compare-package-delta.sh`](scripts/compare-package-delta.sh), with
the resulting comparison in
[`results/package-delta-a9a7-to-c2d9-20260714.txt`](results/package-delta-a9a7-to-c2d9-20260714.txt).

## Findings

- First-boot infrastructure remains built in: the package contains built-in
  MT6797 pinctrl, UART, watchdog, I2C, and eMMC host objects. The MT6797
  pinctrl driver is confirmed by `CONFIG_PINCTRL_MT6797=y` and its vmlinux
  symbols rather than by `modules.builtin` (its `arch_initcall` object is not
  exported there). Other built-ins are listed in `modules.builtin`; their
  module dependency edges are not represented by `modules.dep`. Hardware
  probe order and DT/resource ownership still govern safety.
- AW9523/matrix keyboard, FUSB301, thermal/AUXADC, audio AFE, Panfrost,
  display/media, Bluetooth, and WWAN objects are optional modules. A later
  rootfs must ship the exact closure and matching `modules.*` metadata before
  any controlled consumer test.
- USB MTU3 and several generic transport objects are packaged, but a packaged
  module is not evidence that its Gemini DT node is enabled or that VBUS/clock/
  reset ownership is correct. The closure result must be read together with
  the subsystem DT/package audits.
- The current minimal UART initramfs intentionally contains no module tree;
  this is appropriate for the first handoff gate and is not a claim that
  deferred consumers can work from that initramfs.
- The corrected `c2d9eea95daa` package has identical `Image`, `Image.gz`,
  `System.map`, configuration, Gemini DTB, module count, and every unrelated
  module hash compared with the earlier `a9a7c5002038` package. The only
  module delta is the intended NT36672E panel object, whose hash changes after
  preserving the vendor DCS/generic packet boundary. This lets older subsystem
  package audits remain useful as content evidence while the new package
  identity and panel delta are tracked explicitly.

## Boundary

No module was inserted, no firmware was requested, and no device node or
debugfs state was touched. Runtime loading, symbol resolution against a real
rootfs, and consumer probe behavior remain untested until a non-primary boot
path is available.
