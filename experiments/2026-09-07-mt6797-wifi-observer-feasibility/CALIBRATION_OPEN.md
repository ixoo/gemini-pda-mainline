# Calibration file-open error correction

The [startup filesystem trace](STARTUP_FILESYSTEM.md) found that both native
`nvram_read` and `nvram_write` return after failed `filp_open` without restoring
the address limit saved before `set_fs(KERNEL_DS)`. That leaves the caller with
the kernel address limit. The existing successful-open paths restore it,
including when seek or I/O fails.

The [two-line patch](patches/calibration-open/0001-wlan-restore-address-limit-after-NVRAM-open-failure.patch)
restores `old_fs` on those two open-error exits. It changes no file operation,
return value, calibration bytes or successful-open behavior. This repairs the
native observation kernel; it is not a proposed modern mainline file-I/O API.
The patch carries an explicitly synthetic experiment identity and no DCO
certification.

The [focused checker](check-calibration-open.py) extracts the complete functions
from the checksum-pinned parent and its patched copy. Removing exactly the two
insertions must recover the entire parent source byte-for-byte. Fake file
operations exercise open failure, missing operations table, missing read/write
method, seek failure, direct position fallback, I/O failure, short I/O and
successful I/O. Each runs for both helpers with a user or kernel initial
address limit: 32 cases per version. Assertions check the result, open/close,
seek and I/O counts, the address limit during operations and its final value.
The parent must exhibit the open-error leak; every corrected case must restore
the initial value. No real calibration file is read or written.

Run with a prepared source tree containing the pinned unmodified `platform.c`:

```sh
python3 check-calibration-open.py SOURCE_TREE
```

The [receipt](results/calibration-open.json) records successful host fixtures
and native compilation from clean pushed commit
`27eaa19c4d7e2d1187f4e9a6775ae6f88fce4d8a`. Buildbox held its shared build lock,
verified the existing 41-patch source integrity and complete prior kernel
package checksums, then prepared separate output with the exact linked kernel
configuration. It replayed the archived `platform.c` compiler command for the
parent and corrected complete translation units using pinned GCC 6.3 and native
headers. Both produced AArch64 ELF64 objects. Twelve package files passed remote
validation and checksum verification after fetch. Temporary source/output
copies were removed; the prepared source was not edited.

Strict checkpatch passed with only the missing-signoff category explicitly
excluded for this non-certifying archive. The old native checkpatch script
could not run with the host Perl regex rules; the available Linux 7.3-rc1
checkpatch performed the style check. Native compiler flags inherit `-w`, so
this is not warning-clean evidence. Fixtures ran on the host, not the PDA.

The correction is now the last entry in the 42-patch
[full-kernel inputs](full-kernel-inputs.json), preserving all 41 previous entries
and their order. The canonical upstream series and all profiles are unchanged.
The previously linked image remains the 41-patch image; the correction has not
yet passed a new full link or device test. Startup isolation and boot admission
remain unfinished.
