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

## Build result

The corrected patch at clean pushed commit `0249ba91` applied as the last of
539 selected patches. Buildbox linked Linux 7.1.3 and validated the complete
package inventory; the fetched package rechecked with SHA-256 identity
`becbee6a…ab3aacc7`. The [sanitized receipt](results/build.json) records the
source, patchset, config, image and Gemini DTB checksums. `FW_LOADER`, the
MT6797 wireless core and passive CONSYS owner all resolved to `y`, and
`System.map` contains the three new helper functions. Decompiling the built
Gemini DTB found the passive CONSYS owner and its three VCN supply links, with
no WLAN child or modern CONN compatible. The patch adds no runtime caller.

Strict Checkpatch has no remaining source-style finding. Its missing DCO
sign-off error and MAINTAINERS warning are retained because this is an
internally authored proposal with synthetic, non-certifying identity. The
first build from `4467d3ee` was superseded by this allocation-style correction;
it is not the accepted package. No firmware blob was transferred, and no PDA
boot or radio action occurred.

## Retained-image C planner check

The [sanitized check](results/retained-plan.json) ran the pinned C MTKE parser
and complete-image planner against the exact private 411,632-byte Gemian WLAN
image. The plan accepted all four sections: two ordinary sections totaling
14,832 bytes and two EMI sections totaling 396,688 bytes. Without an EMI owner,
admission returned the expected `-3` refusal and the first ordinary-section
request yielded no executable view. This checks the actual image against the
planner used by the compiled preparation helper; it does not call that Linux
helper, touch the PDA, or establish firmware execution. The private bytes stay
under ignored `artifacts/firmware/`.

In a bounded read-only check of the changed-boot Gemian system, the
[installed file identity](results/gemian-file-identity.json) matched the same
retained SHA-256 and 411,632-byte length at
`/vendor/firmware/WIFI_RAM_CODE_6797`; WLAN carrier was present. The boot ID
was unchanged across the check. This connects the private input to the file
currently installed on this PDA, not to a proven historical loader read or a
mainline firmware search path.

To repeat the check locally with the retained image, run
`python3 -B experiments/2026-09-27-mt6797-wifi-firmware-prepare/scripts/verify-retained-plan.py artifacts/firmware/gemian-2019-vendor/vendor/firmware/WIFI_RAM_CODE_6797`.
