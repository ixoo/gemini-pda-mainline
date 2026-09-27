# MT6797 WLAN firmware preparation

The [passive CONSYS owner](../2026-09-27-mt6797-consys-rails-passive/README.md#passive-device-result)
now holds real VCN handles, while the selected WLAN code has an MTKE parser and
complete image planner but no kernel firmware acquisition. This slice adds that
missing software boundary without attaching a WLAN child or attempting a
hardware transition.

The [internal format patch](../../patches/proposals/0027-wifi-mediatek-prepare-immutable-MT6797-firmware.patch)
uses `request_firmware()` for `mediatek/mt6797/WIFI_RAM_CODE_6797`, retains the
returned immutable buffer with its validated complete plan, and permits only
descriptive section metadata to escape. Oversize, invalid and unsupported
images fail before an object is published; the firmware buffer is released on
every failure. No payload view, HIF transaction, rail, reset, remap, EMI,
firmware START, radio or DMA action is exposed. The original image binding and
its owner-required refusal remain unchanged.

The new `mt6797-a53-wifi-firmware-prepare-compile` profile extends the
successful A53 passive-rails series in canonical order. It retains the same
Gemini DTB and configuration fragments. The new helper has no caller, so a
kernel build can establish source integration only. Its fixed firmware name
follows the retained installed file's observed identity; the file bytes stay
private and are not packaged or redistributed by this change. The eventual
WLAN client must acquire the firmware after its shared-owner binding and keep
the plan alive through a confirmed effect-bearing lifetime.

## Build decision

The compile hypothesis is that the pinned Linux 7.1.3 source applies the one
new patch, resolves `FW_LOADER` with the selected A53 configuration, and links
the helper into the MT6797 WLAN object without adding a DT child or runtime
call. A patch/config/compiler/link failure redirects source repair; a changed
DTB or an unexpected runtime caller refuses promotion. Build from a clean
pushed commit with:

```sh
KERNEL_PROFILE=mt6797-a53-wifi-firmware-prepare-compile ./scripts/build-kernel --backend buildbox
```

This package is not a boot2 candidate. The next useful code is the permanent
owner's serialized effect and retained-fault contract, followed by a staged
WLAN child that can bind this preparation to an owned downloader epoch. EMI
master routing, overlapping-region applicability and external-writer exclusion
remain prerequisites for a firmware-execution device test.
