# Keyboard monitor compilation input review

Bounded host-only review of the [monitor proposal](MONITOR.md), its complete
source, fixture and test compile arguments. No backend connection, compilation,
new library download, device access or delivery admission occurred.

| Reviewed source | SHA-256 |
| --- | --- |
| `monitor.c` | `fa8c25fe4be461759bc8f720ce52a7cb8ff8319861390e26d69ab0a46073c67b` |
| `monitor-fixture.c` | `8bf4e30c410d5146bb5ef8549873dbb46144b23cd929f2973c0b11965796ae90` |
| `test-monitor.py` | `4274fbc6ab33737619d9e274fe85b2da15dca1f65f682549beac00bb59a351bd` |

The compiler and linker hashes in the proposal match the retained baseline
userspace package's `provenance.txt` for package manifest
`dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60`.
This confirms agreement with historical provenance, not current builder bytes.
The proposal already requires checking those bytes and resolving the compiler's
additional tool, startup, header and library inputs in an assigned window.

The production source uses libc-provided signal/wait structures and Linux's
`SYS_close_range` header definition. Its default `main` returns refusal. The
external `keyboard_monitor_run` symbol must remain rooted during section garbage
collection; checking only the disabled entry's size would omit the intended
engine. The proposed explicit undefined-symbol link option addresses that
boundary; the link map still needs inspection on the actual target link.

The host fixture selects its harmless child and shortened deadlines at compile
time. It therefore cannot establish production-duration behavior or the ARM64
Linux header/syscall boundary. The proposed target fixture and independent full
duration check remain necessary; host results are not promoted here.

The musl archive/license/configure pins are a documented proposal only. This
review did not independently redownload or authenticate that archive. No admitted
musl library, complete resolved toolchain manifest, ARM64 link map, replica
comparison or stripped executable size is available from this review. The
131,072-byte delivery limit remains unmeasured. These are retained proposal
boundaries, not new execution authorization.
