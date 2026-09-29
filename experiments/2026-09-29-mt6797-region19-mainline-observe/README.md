# Passive mainline region-19 preflight

The [known-good Gemian read](../2026-09-29-mt6797-region19-live-reference/results/runtime-1.json)
found populated, changing data in the second 512 KiB of the CONSYS
reservation. The [firmware-start boot](../2026-09-28-mt6797-firmware-start-probe/results/runtime-1.json)
did not initialize this WMT control window and later panicked for an
unattributed workqueue reason. The preflight asks whether region 19 still
contains nonzero data in a fresh mainline boot **before** any CONN power,
firmware or EMI transition. It does not retry START.

[Patch 0046](../../patches/proposals/0046-soc-mediatek-observe-reserved-MT6797-region19.patch)
adds one DT-gated, read-only sample after the exact boot reservation guard.
The named profile removes the preceding diagnostic's power, reset, HIF, EMI
and START flags. The kernel maps only the neighboring 512 KiB and logs its
nonzero byte count, populated 4 KiB page count, and first/last populated
page; it neither emits memory contents nor writes that window. A runtime
gate rejects a simultaneous power probe. Passive CONSYS and WLAN firmware
preparation bindings remain available for the usual A53 service regression.

The one-boot hypothesis is that this early mainline sample will distinguish
an empty window from retained data before a new firmware executor is
designed. A nonzero result requires preserving and attributing any unique
content before an owner clears the WMT extent. A zero result still does not
establish the required control-memory initialization or effective protection.
A missing result, failed guard or kernel fault stops this path for diagnosis;
none authorizes START or an alternate recovery. The unique receipt requires
the exact candidate/full boot2 readback, changed authenticated mainline boot,
one region-19 record, complete kernel log, A53 regression and confirmed
changed-boot Gemian return.

The source profile is `mt6797-a53-wifi-region19-observe`. Build only its clean,
pushed commit with:

```sh
KERNEL_PROFILE=mt6797-a53-wifi-region19-observe ./scripts/build-kernel --backend buildbox
```

Validate the package, DT flag,
kernel release, initramfs and LK container before guarded boot2 installation.
The owner physically selects boot2 after the host collector is armed. The
previous firmware-start image must not be replayed. Raw evidence, firmware
and credentials remain ignored under `artifacts/`.
