# START and immutable image-binding Buildbox acceptance

The explicit `mt6797-hif-parser-compile` Buildbox build completed at
`387642749402421324f1b5710f5efe335ec5fa63`. The normal helper fetched only
its validated package. Source, object and disassembly inspection stayed on the
backend; no kernel source tree or object was transferred.

| Identity | SHA-256 |
| --- | --- |
| Package inventory | `b2a39af6bbe61ab931d00570da9b0d48b28515f479b9f85c5a227f83410aaae3` |
| Source archive | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Eight-patch set | `a23db933cb92e7099ad77da0f2cf6002c0915a480d49c8cb42189725108ee696` |
| Resolved configuration | `b7c37fa4b68056470ef392a9d6eef55cd3b56f5310ed9e20fbf91b31231c3282` |
| Image.gz | `b0e59777654b81ad1a6acdb177f5b67f9caa6cb5b78b36d146dedc1c076c70dc` |
| hif.o | `c05ade2795d240eab17c8a2bf5dd3f17fc3f93a80eb74431661f78f418eda6d8` |
| image-binding.o | `f62d02ee58404d8fa8dbfb4ec63576135145514586ba951672ba8a8870de7a2e` |

The package validator accepted all checksums, provenance and 118 DTBs, with
release `7.3.0-rc1-mt6797-hif-parser-compile`. The configuration is identical
to the [preceding complete-plan build](../2026-09-05-mt6797-whole-image-plan/BUILD_RESULT.md).
The existing shared provider source path was refreshed for the changed patch
set under the Buildbox lock; no experiment-specific Linux copy was created.

Backend source hashes match the reviewed START `hif.c/h` identities in
[inputs.json](inputs.json) and the binding `image-binding.c/h` identities in
[its proposal](../2026-09-05-mt6797-image-binding/proposal.json). The parser,
CRC adapter and complete-plan source identities are unchanged. Their objects
also remain byte-identical to the preceding accepted build: image-plan.o
`55b8176a6fafd69ab06004a39e322b22e06bc5888be9a9ab7bfd4f7c88c74d0a`,
mtke.o `85b9edb8d80b226a86eb6d8ddaa78c04f874ffed251795ae470b8e356b2f4666`,
and crc-kernel.o `77803e5c638a2ff1e63cec3f9ac59cc3f1fcc9e4d107c3f517eca9bfe40ae034`.

All five private objects have AArch64 headers and real kernel compilation
commands without host-test macros. The private archive contains all five.
All six HIF, twelve binding/owner, five complete-plan and three parser/CRC
functions are nonzero global FUNC definitions, with matching definitions in
vmlinux and System.map. Undefined references connect the binding to the real
image-plan functions, kernel allocation/free, memcpy and mutex operations.
The HIF uses the real clock, mutex and sleep functions; CRC still refers to
crc32_le. No private object has initcall/export sections or the test-only
generation hook.

Disassembly confirms START latches its attempt and deadline before entering
validation, consumes TC0 and sequence history, then invokes the real PIO
transfer for port 0x34. The scalar write has `dmb oshst` before its 32-bit
store; the FIFO read at offset 0x1000 has `dmb oshld` after its 32-bit load.
Both retain the surrounding absolute-deadline checks. Readiness uses the
latched deadline, calls the logical-register read path for WCIR and tests
bit 21; it does not acquire a new budget. Binding begin retains validation
errors or returns -95 (EOPNOTSUPP), never active success.

Result: compilation and linkage accepted for both deltas. No runtime caller,
resource acquisition, firmware load or device boot was exercised or selected.
This is not Wi-Fi hardware support. The synthetic non-certifying authorship
and disclosed Checkpatch metadata findings remain unsuitable for upstream
submission. Real shared resource ownership and complete execution remain
separate prerequisites.
