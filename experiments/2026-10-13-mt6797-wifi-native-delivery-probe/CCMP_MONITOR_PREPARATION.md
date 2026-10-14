# CCMP monitor compatibility — build and composition preparation

This is **a validated build/fetch, not a boot or Wi-Fi result**. ROOT approved
the final source and separate ND6+0190+0191 selection. See the
[source/selection review](CCMP_MONITOR_INTEGRATION_REVIEW.md) and
[real build pins](results/ccmp-stable-monitor-build.json).

Kernel input is clean pushed `83b91a6c54e45159763f62652b14710670bf895f`, profile
`mt6797-a53-wifi-ccmp-stable-monitor`,32 jobs/modulesfalse/ordinary provenance on
Buildbox-1. The managed validator completed and fetch verified the exact package
inventory/provenance. All actual built driver files match final source9b7bad2.
Resolved config SHA256 is483e0165; its complete bytes equal C32's config plus only
the reviewed identity/release/mode/symbol changes. No API/type fix or rebuild was
needed. No historical profile was built.

## ROOT composition (offline, no extra assembly permission)

Use [the compositor](build-ccmp-candidate.py) with the validated exact package and
the existing private C32 parent. It checks all parent/package identities, the
whole kernel config, unmodified board DT/SMC/clock contract, exact64-member RAM
(only init release gate changes), boot container and exact full-partition padding.
It emits a **real** candidate receipt, without performing a device action.

```sh
BUILDBOX_HOST=buildbox-1 KERNEL_PROFILE=mt6797-a53-wifi-ccmp-stable-monitor BUILD_MODULES=0 ./scripts/buildbox fetch-package
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/build-ccmp-candidate.py --kernel-package <validated-package> --parent <private-C32-parent> --output <new-private-output>
```

The package remains pinned to kernel input83b91a6c even if later **tooling-only**
commits publish the compositor/bindings. No binding-only kernel rebuild. The
fetched package is under ignored `artifacts/buildbox/83b91a6c.../linux-7.1.3-gemini-f07c722c.../`.
Choose a fresh output directory; a real candidate receipt and all image digests
must be returned before receipt-bound runtime/installer code is finalized. No
placeholder receipt, candidate checksum or live boot identity is supplied here.

Focused compositor tests compare a reconstructed, hash-verified **non-secret**
C32 config with the real new package and test parent/config mutations. They do
not read the private parent or prove its RAM/container composition. ROOT's actual
compositor run performs those gates. Runtime/installer/binding preparation is
ongoing; do not use a historical native installer/session for the new mode.

First runtime stays normal DHCP only, helpers prepared before ACTIVE, WLAN-bound
ping and fresh boot/mode-bound SSH within the real finite ACTIVE window. Failure
or short window is a partial result. GTK RX, normal producer, rekey/reuse,
IRQ-DMA reliability and clean-profile ten-minute Wi-Fi SSH remain unresolved.
Only ROOT operates the device and private C32/RAM. Guarded install/full readback/
clean shutdown and owner physical boot2 remain mandatory after real bindings.
