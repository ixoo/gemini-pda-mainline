# Build result

Buildbox compiled and validated repository commit
`086c2f24f7edf29156f440fa9ba160e59711856f` with the isolated
`mt6797-hif-parser-compile` profile. Job
`086c2f24f7edf29156f440fa9ba160e59711856f-mt6797-hif-parser-compile-m0`
completed at `2026-09-06T15:00:30Z`, produced release
`7.3.0-rc1-mt6797-hif-parser-compile`, and validated package inventory
SHA-256 `630f80ff1bf03ff798570e357e351139649ebfb74bfd116a8e6030f851e3c5ab`.
The package was fetched only through `scripts/buildbox fetch-package` beneath
the ignored Buildbox artifact tree.

| Identity | SHA-256 |
| --- | --- |
| Upstream source | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Fifteen-patch set | `ab6134d2d21c48869592d1dbde6c1cf3babe2e796e5e69409d38ddd80199f191` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| `Image.gz` | `5f8257eed7d85bf6fe483f5cd06776d4257747f8065146b915c1c5ae7ad0fdf5` |
| `ordinary-transfer.o` | `cc57b69bcbb11c6237a5f69479fcb8ad50a1b3862dd7a98d1013a52cbf7bb59f` |
| Object command record | `b52073682ae1eeffe4ffba4bdb5379761fbe6ee71610d4aa127917a40be85f09` |

The real object is ELF64 little-endian AArch64, is not stripped, and is a
member of the private MT6797 built-in archive. Its command record uses
`ccache aarch64-linux-gnu-gcc`, defines `__KERNEL__`, names the exact prepared
source and does not define the host-test macro. The object defines nonzero
`mt6797_ordinary_transfer_prepare`, `mt6797_ordinary_transfer_execute` and
`mt6797_ordinary_transfer_free` symbols. Its undefined
`mt6797_hif_download_section` reference resolves to the separately compiled
real HIF definition in final `vmlinux`. Prepared-source and experiment C/header
hashes match exactly. A complete prepared-source search finds only the bridge
declarations and definitions and no production caller, initcall, export or
registration.

Pinned strict Checkpatch reports zero checks and only the expected synthetic
missing-DCO error and new-file/MAINTAINERS warning. Those findings are retained:
the experiment uses a synthetic non-certifying author and cannot truthfully add
a DCO sign-off, and its temporary private WLAN placement is not
submission-ready. Checkpatch's optional SPDX helper could not import the
Buildbox `ply` module; the SPDX identifiers were independently covered by the
repository license checks and direct source inspection.

The package validator accepted its complete inventory, exact source, profile,
configuration and fifteen-entry proposal series. This proves Linux types,
AArch64 compilation, linkage to the existing HIF entry point, and absence of a
linked runtime caller. It does not prove whole-image admission, real owner or
generation lifetime, exclusion, firmware readiness, complete-image execution,
hardware transfer or usable Wi-Fi. No device was accessed, and no boot
candidate or hardware write was created.
