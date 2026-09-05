# Recovered BusyBox package provenance

The retained initramfs binary is byte-identical to Ubuntu's
[`busybox-static_1.36.1-6ubuntu3.1_arm64.deb`](https://ports.ubuntu.com/ubuntu-ports/pool/main/b/busybox/busybox-static_1.36.1-6ubuntu3.1_arm64.deb),
downloaded from the official archive during this preparation. Package SHA-256:
`d96535e0402c011e0ee43449799df2f4504d44b842e4f2b3a6cbc845508eaafc`.
Its `usr/bin/busybox` is 1,914,704 bytes with SHA-256
`52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`,
exactly matching the inherited `/bin/busybox`. Its embedded banner reports
BusyBox 1.36.1, Ubuntu `1:1.36.1-6ubuntu3.1`.

The package copyright file is 1,110 bytes, SHA-256
`336d995e819d3a7a3fdbf3f5041c07094f75ee849acb3bb742b7503d45786329`.
Keep it with the private userspace package. The official
[source descriptor](https://ports.ubuntu.com/ubuntu-ports/pool/main/b/busybox/busybox_1.36.1-6ubuntu3.1.dsc)
names these corresponding sources:

| Source | SHA-256 |
| --- | --- |
| `busybox_1.36.1.orig.tar.bz2` | `b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314` |
| `busybox_1.36.1-6ubuntu3.1.debian.tar.xz` | `1c7d785cf1e1d5d09ddc22fe755e14327fb3799878a5d840fc611044ff05f022` |

This closes identification of the public binary package and its declared
source package. It does not claim an independent source rebuild, authenticated
archive-signature verification, current security suitability for unrestricted
networks, or complete binary-distribution compliance. The new candidate
retains the runtime-proven binary for a bounded private direct-USB experiment.
Exact shell tests can now fetch the public package on Buildbox, verify both
package and binary hashes, and discard it after testing; no candidate or
private evidence transfer to the builder is required. The earlier audit's
unresolved provenance statement describes its earlier audit stage.
