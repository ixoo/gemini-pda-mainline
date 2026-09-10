# Private startup input filesystem

On 2026-09-10, the [builder](build-startup-filesystem.py) combined the
[tested runtime](RUNTIME_NATIVE.md) with five verified retained inputs in the
RE VM. The [sanitized receipt](results/startup-filesystem.json) records the
result. This is an incomplete input filesystem: it has no `/init` or trigger
and is not a boot candidate.

The four firmware/configuration files matched their retained corpus manifest.
The calibration input came from the verified private partition backup: its
manifest, successful capture status, image size and full image checksum were
checked before read-only `debugfs` extraction of `/APCFG/APRDEB/WIFI`. Extraction
required a successful status, only the expected version line on stderr and
exactly 514 bytes. The existing storage inspector accepted the envelope and
the independently selected driver version context. All 514 bytes, including
the storage trailer, were preserved unchanged. The
[provenance limitations](../2026-09-05-mt6797-wifi-contract/PROVENANCE.md)
continue to apply.

## Selected lookup layout

| Input | Path inside the filesystem |
| --- | --- |
| Common connectivity configuration | `/lib/firmware/WMT_SOC.cfg` |
| Two retained connectivity patches | `/lib/firmware/ROMv3_patch_1_1_hdr.bin`, `/lib/firmware/ROMv3_patch_1_0_hdr.bin` |
| WLAN firmware | `/vendor/firmware/WIFI_RAM_CODE_6797` |
| Retained WIFI storage file | `/data/nvram/APCFG/APRDEB/WIFI` |

The exact prepared 41-patch source identified by full input manifest
`8eb70ddef491146e7d7f47c0226f9b9565c68da2c4aa96e0857e88ad36b585cf`
selects `WMT_SOC.cfg` for its SoC path and uses `request_firmware` for the
common configuration and patches. WLAN checks `/storage/sdcard0` before
`/vendor/firmware`; the former is absent. Firmware update and kernel-version
subdirectories are absent. Future startup must also verify that the kernel's
firmware-path override is empty before admitting these lookups.

The full-kernel compilation recorded no `ENABLED_IN_ENGUSERDEBUG` define for
`gl_init.c`, so its engineering `wifi.cfg` loader is excluded. The separate
crystal-trim helper is excluded by `CFG_WMT_CRYSTAL_TIMING_SET=0`. The active
WIFI reader consumes the logical 512-byte portion at the selected path;
`WIFI_CUSTOM` is not an input to that reader.

Tracing this path also found a prerequisite kernel defect: `nvram_read` and
`nvram_write` in WLAN `os/linux/platform.c` set `KERNEL_DS` before `filp_open`
but return on open failure without restoring `old_fs`. The source file matches
the earlier [consumer pin](../2026-09-05-mt6797-wifi-contract/CALIBRATION.md).
This is a source observation, not an observed device failure. The correction
and its native compilation are still pending.

## Packaging and validation

Run the builder on Linux in the RE VM with GNU tar, cpio and gzip, using private
inputs already verified against their original manifests:

```sh
python3 build-startup-filesystem.py PRIVATE_INPUTS RUNTIME_TAR NEW_PACKAGE
```

The private input directory contains only the five named files and
`manifest.json`; its `files` object maps each basename to `size` and `sha256`.
Keep this directory and output private. Serialize access to the output parent:
the builder removes its `.wifi-startup-filesystem-*` unfinished staging there.
The builder pins the tested runtime, validates all five files and the existing
patch/storage contracts, and creates a normalized gzip/newc archive. Input
files have mode 0400; that does not enforce immutability against root. Startup
still needs explicit read-only mounts and exact session admission.

An independent newc parse checked all 1,622 members, root ownership, zero
timestamps, allowed file types, unique relative paths, exact five input hashes,
0400 input modes and absence of init and alternate lookup files. Package
checksums passed in the VM and after export; host output permissions are
restricted. The compressed filesystem is 23,568,419 bytes. The private package
contains its complete input identity and checksums, which are not published.
No new kernel build or device operation occurred in this slice. PID1, capture
preparation, kernel actor/reset isolation and boot admission remain unfinished.
