# Experiment: mainline handoff closure audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-mainline-handoff-closure` |
| Status | `completed` for static package closure; runtime boot remains untested |
| Subsystem | arm64 entry, PSCI/timer/GIC, UART console, eMMC, memory handoff |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date | 2026-07-13 |

## Question

Does the current Linux 7.1.3 package contain the built-in handoff pieces and
DT resources needed for the first reversible Gemini boot candidate, without
silently reintroducing the old post-LK memory snapshot?

## Method and limits

The audit is read-only. It checks the packaged `kernel.config`, `System.map`,
and Gemini DTB in the development VM. It does not boot, flash, open a serial
device, or claim that a built-in symbol has successfully driven hardware.
Dynamic reservations are checked by name and policy; the allocator's runtime
placement is still a boot-time observation.

Run it against a package produced by `./scripts/dev-vm build-kernel`:

```sh
./scripts/dev-vm run env \
  CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2d9eea95daa \
  experiments/2026-07-13-mainline-handoff-closure/scripts/validate-handoff-closure.sh
```

## Interpretation

The closure is intentionally narrow: it verifies the configuration and static
contracts that must be present before a controlled boot attempt. It does not
validate regulator sequencing, pin electrical state, LK command-line mutation,
or the vendor AP-DMA UART extension. A future failure should therefore be
attributed to the earliest missing runtime contract, not treated as proof that
the corresponding upstream driver is wrong.

When a non-primary mainline candidate has actually booted, capture the bounded
runtime handoff with the read-only harness below. It does not flash, reboot,
bind/unbind, scan a bus, use sudo, or write a device; its output belongs under
the Git-ignored `artifacts/` tree:

```sh
experiments/2026-07-13-mainline-handoff-closure/scripts/collect-mainline-runtime-evidence.sh \
  --target gemini@192.168.1.50 --kind mainline-candidate
```

The capture records sanitized identity/cmdline, CPU online/possible/policy
state, final reserved-memory names and ranges, `/proc/iomem` ownership hints,
timer/PSCI/IRQ state, linked modules/devices and platform-driver bindings,
console ownership, dmesg, eMMC identity, regulator/watchdog state, and
debugfs summaries when readable. It is a post-boot observation tool only; it
does not turn a static package result into a hardware-support claim. The
collector labels the capture kind and reports the observed kernel release; it
deliberately leaves `runtime_mainline_boot` for comparison against the
candidate's expected release and final handoff DTB. Use `--kind vendor-baseline`
when capturing the existing Gemian image so a vendor snapshot is not mistaken
for a mainline boot.
The dmesg tail is bounded to 120 lines, and a failed SSH session is marked in
the mode-0600 output rather than leaving an insecure partial capture.

The earlier authorized access attempt is retained in
[`results/runtime-access-attempt-20260714.txt`](results/runtime-access-attempt-20260714.txt)
as negative network evidence. A later bounded SSH session succeeded against the
existing Gemian image, and the collector captured a sanitized vendor baseline;
see [`results/vendor-baseline-runtime-20260714.txt`](results/vendor-baseline-runtime-20260714.txt).
That capture reports the vendor `3.18.41+` kernel and is explicitly not a
mainline boot result. The raw capture remains mode-0600 under the Git-ignored
`artifacts/device-inventory/` tree.

After the device returned from a battery-depletion reboot, the same bounded
vendor-baseline collector completed again. The post-reboot result confirms the
same 3.18.41+ ownership split, ten-CPU possible/present topology with only
CPUs 0–1 online at capture, DF4064 eMMC identity, and dynamic LK reservation
classes: [`results/vendor-baseline-postreboot-20260714.txt`](results/vendor-baseline-postreboot-20260714.txt).
It is still a vendor comparison capture, not a mainline boot result.

A second battery-recovery capture at 16:23 UTC found the same kernel,
driver-ownership split, DF4064 identity, and reservation classes. This snapshot
reported CPUs 0–2 online while possible/present remained 0–9; the prior
post-reboot snapshot reported 0–1 online. That delta is explicitly treated as
time-dependent vendor hotplug/policy state, not as evidence for or against
mainline SMP. The sanitized comparison is
[`results/vendor-baseline-battery-recovery-20260714.txt`](results/vendor-baseline-battery-recovery-20260714.txt); the raw capture remains
mode-0600 and Git-ignored.

See [`results/handoff-closure-current-20260714.txt`](results/handoff-closure-current-20260714.txt)
for an earlier package summary and [`results/handoff-closure-current-72-package-20260714.txt`](results/handoff-closure-current-72-package-20260714.txt)
for the authoritative corrected c2d9 package hashes and audit output. The
older `handoff-closure-20260713.txt` record remains historical provenance.

The current 72-patch package rerun is recorded separately in
[`results/handoff-closure-current-72-package-20260714.txt`](results/handoff-closure-current-72-package-20260714.txt).
