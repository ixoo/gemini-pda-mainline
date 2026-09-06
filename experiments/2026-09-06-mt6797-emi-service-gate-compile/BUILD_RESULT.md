# Build result

Buildbox compiled and validated repository commit
`d1a0f9a9d840c4f050871b5128dc06aefb897214` with the isolated
`mt6797-hif-parser-compile` profile. Job
`d1a0f9a9d840c4f050871b5128dc06aefb897214-mt6797-hif-parser-compile-m0`
completed at `2026-09-06T07:31:35Z`, produced release
`7.3.0-rc1-mt6797-hif-parser-compile`, and validated package inventory
SHA-256 `d026dedd107b0f94cc7c521a4689f4d25e03dedeefd154fe5344816435533a51`.
The package was fetched only through `scripts/buildbox fetch-package` beneath
the ignored Buildbox artifact tree.

| Identity | SHA-256 |
| --- | --- |
| Upstream source | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Fourteen-patch set | `38011ee2b838f4365da2c81f277d7a41137ddbcb9c6c6a69b857870d92937e01` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| `Image.gz` | `3d676213010ed91666f4d1be9c8fa2469353efdac307e954625f81fee1d01ef2` |
| `emi-service-gate.o` | `3ace5752b66f93d40ce0ba88dd012b0404cf76b39f2d377e648ea03ef9887b6f` |
| Object command record | `18768a5dfd9491848f84a387b03b25efca2ec3c32581582a7d6d645f5f279a6f` |

The real object is ELF64 little-endian AArch64, is not stripped, and is a
member of the private MT6797 thin built-in archive. Its command record uses
`ccache aarch64-linux-gnu-gcc` and defines `__KERNEL__` exactly once. The
object defines `mt6797_emi_service_gate_init` and
`mt6797_emi_service_gate_apply`; its undefined references to
`mt6797_emi_prepare`, `mt6797_emi_decode_result`, and
`mt6797_remap_encode_common` resolve to the separately compiled predecessor
definitions in final `vmlinux`. Its source and header hashes exactly match the
experiment sources. A complete prepared-source search finds only one
declaration and one definition of each gate API and no caller. The existing
active binding refusal still returns `-EOPNOTSUPP`.

Pinned strict Checkpatch reports only the expected synthetic missing-DCO error
and new-file/MAINTAINERS warning. Those findings are retained: this internal
experiment deliberately uses a synthetic non-certifying author and cannot
truthfully add a DCO sign-off, and its temporary private WLAN placement is not
submission-ready.

The package validator accepted its complete inventory, exact source, profile,
configuration and fourteen-entry proposal series. This proves Linux types,
compilation, linkage, predecessor-interface composition and absence of a
linked runtime caller. It does not prove a deployed secure service,
reservation lifetime, selector stability, external-writer exclusion,
serialization, permission policy, firmware compatibility, visibility,
recovery or Wi-Fi support. No device was accessed, and no boot candidate or
hardware write was created.
