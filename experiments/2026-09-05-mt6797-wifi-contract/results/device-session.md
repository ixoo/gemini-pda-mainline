# Admitted Wi-Fi reference-system session

Date: 2026-09-05 UTC. Coordinator assigned the bounded Wi-Fi inspection slot
after the owner authorized inspecting Gemian and existing private firmware.
The previous CPU workstream confirmed it would make no device access and
that [V4 runtime evidence](../../2026-09-04-mt6797-thermal-snapshot/results/v4-runtime-pass.txt)
was preserved. Its attempted detailed handoff was blocked by automatic review;
only published references were exchanged. The Wi-Fi worker independently
established the current identity using existing access instructions.

## Reviewed return to Gemian

An initial bounded SSH identity connection to the known Gemian endpoint timed
out. The host's existing USB route selected the direct link. A metadata-only
query over the retained direct-link recovery shell observed:

- release `7.1.3-gemini-thermal-v4-corrected`;
- boot ID `27216ca5-494f-450b-867d-243cd906e6b9`, matching the completed V4 record;
- BusyBox SHA-256 `52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`;
- `/bin/reboot` SHA-256 `3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7`;
- only rootfs, devtmpfs, proc and sysfs mounts, with CPU0-7 online.

The reboot bytes match `AB_REBOOT_BYTES` in the
[reviewed native-restart validator](../../2026-07-20-mt6797-kernel-restart-diagnostic/scripts/validate-initramfs.py).
The BusyBox digest matches the
[inherited USB candidate validator](../../2026-07-21-usb-gadget-ethernet/scripts/validate-initramfs.py).
A narrowly guarded shell rechecked those exact identities and mount classes,
then invoked `/bin/reboot` once. Its Bash syntax and ShellCheck checks passed.
The native wrapper reached the reviewed BusyBox `reboot -n -f` path; no
partition write, watchdog request, thermal sample or boot2 selection occurred.
The prior USB recovery endpoint disconnected.

Known-host, key-authenticated SSH subsequently returned vendor release
`3.18.41+` and changed boot ID `65ad474e-847b-4d48-880a-9693d5d1c7b1`.
Python was `3.5.3`. The known-host identity was required; no host-key bypass
was used. SSH traffic may use stock Wi-Fi and is not a claim of radio silence.
The stock connection also produced host-key-update/locale warnings; the later
collector disabled optional known-host updates and retained stderr privately.

This confirms the observed return to Gemian, not a general reboot reliability
claim. The old thermal budget remains consumed. Raw recovery/probe stdout and
stderr and the exact transition shell remain under the private mode-0700
ignored `artifacts/wifi-parent-attribution/20260905-inspection/` root, with
mode-0600 files. No credential or raw artifact is part of the Git handoff.

## First parent discriminator

The first collector was frozen at SHA-256
`c89820e47e499fd6bc5ebc39846125ab7e64fd38df12a17bdb4ddc58c8489d65` after
40 synthetic tests and a Python 3.5 compatibility review. An actual streamed
Gemian dry run passed without metadata reads. One explicit collection then
returned the [sanitized JSON receipt](parent-attribution-v1.json).

Observed: expected boot and kernel matched through the end; model matched
MT6797X; standard SDIO enumeration completed with zero entries; the WLAN
ancestry chain returned `metadata_unavailable`. Attribute payload reads
totalled 100 bytes. The classifier returned **inconclusive**, exit 2.

That read total covers identity twice and the model only. It does not identify
which WLAN link/property was unavailable. Absence of standard SDIO entries
does not establish a missing physical function: selected gen3 implements a
private SDIO-like shim over AHB. A separate source audit identified that the
platform probe can bind before a later WMT callback creates the netdev; this
is a possible explanation, not a measured Wi-Fi activation state.

The sole first-protocol attempt is consumed. No identical retry was made.
A distinct fixed-name presence diagnostic was proposed for review to localize
the missing link, with no radio operation or attribute-payload read beyond
identity. Its admission and any result must be recorded separately. Current
radio, firmware execution, association, traffic and stability remain unproven
by these observations.

## Separately admitted eight-path follow-up and release

Project Planning admitted the distinct follow-up on the same verified Gemian
boot, with eight fixed logical paths and a ten-second collector deadline.
The [session packet](../SESSION.md) recorded its hypothesis and budget before
execution. The original helper stayed frozen; the diagnostic was SHA-256
`f2e5e344b81d4f4faee1e56b602f02c460aba9f62d148e2026714f3025b27fcd`.
Fifteen focused tests and actual Python 3.5 dry-run execution passed before
its single collection. The [complete sanitized receipt](parent-presence.json)
preserves the classifier's exit 2 / **inconclusive** outcome.

The result nonetheless establishes these individual metadata observations:

- `wlan0` resolves under the expected `180f0000.wifi/net/wlan0` device;
- its `device` link resolves to `180f0000.wifi`;
- its subsystem is platform and its driver is `mt-wifi`;
- the independently named platform-device driver link also matches `mt-wifi`;
- the OF node link is unavailable, so `compatible` and `clock-names` through
  that link are unavailable too.

Only 92 identity bytes were read, with no property-payload reads. The expected
kernel and boot ID matched through the end. Thus direct platform ancestry is
observed, while the full original OF check remains incomplete. This rejects
the absent-netdev explanation for this follow-up and localizes v1's failure
to OF exposure. It does not prove that the installed driver is byte-identical
to the public selected-source tree; its uppercase/lowercase compatible
discrepancy remains separate.

Both metadata budgets are consumed. No identical retry, driver operation or
radio control occurred. Wi-Fi custody was explicitly released to Project
Planning after the follow-up, with the device left running Gemian and no
pending Wi-Fi observer. The A53 and CPU workers were notified. Firmware
analysis used the existing RE VM, whose interactive session was closed after
the metadata result; no firmware was copied or loaded.
