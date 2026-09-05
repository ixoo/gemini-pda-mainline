# Buildbox compilation result

The compile-only `mt6797-hif-compile` profile passed on Buildbox at project
commit `7d3c0a316095d1e75b51a2e4bb8ff10181c31b48`. The explicit Buildbox build
and validated-package fetch both completed. No device operation was performed.

| Identity | Value |
| --- | --- |
| Release | `7.3.0-rc1-mt6797-hif-compile` |
| Package inventory SHA-256 | `91a0053071e3c93baf46b0e0cd61efd7f4c0812da2c389beead4e9d64c61d91c` |
| Source SHA-256 | `45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` |
| Patchset SHA-256 | `8361d7fa128823a9cde1e526b6c26edc1a3b51387fbd70c6d94be82a4083950e` |
| Resolved configuration SHA-256 | `75837263911a0a35c2a39d20f6c11ade39df5676684b5dda4ad8b14c8f7f2487` |
| Image.gz SHA-256 | `9c5e9272b907dbeaac9fe4686671ad2607abfa7acd0b836ff40258ba0a874ed4` |

The managed builder refreshed the shared provider source with its three selected
patches, compiled and linked the kernel, and validated all package checksums,
provenance and 118 DTBs. The fetched inventory matched the validated job record.
The host export remains under ignored `artifacts/buildbox/` at the exact commit.

Both `CONFIG_COMPILE_TEST` and `CONFIG_MT6797_HIF_COMPILE_TEST` resolved to `y`.
The job log records `CC lib/mt6797-hif-compile/kernel_adapter.o`; its
`warning:`/`error:` scan returned no matches. Backend `nm --defined-only` found
the eight global wrappers: bind, pio, section_begin, section_ack, section_next,
start_begin, start_submitted and start_ready, all prefixed `mt6797_compile_`.
The local read/write callbacks and inline PIO implementation were also emitted.

Backend objdump inspection found `.text` size `0xbe4`, empty data/BSS and no
initcall or exported-symbol sections. The write callback emits `dmb oshst` then
the scalar store; the read callback emits the scalar load then `dmb oshld`.
This proves code generation, not real-device ordering or bus-fault recovery.
Source inspection confirms no runtime registration or caller.

The accepted result covers the existing compilation scaffold only. The separate
MTKE parser, private HIF core and normal-command proposals were not compiled by
this profile. No boot container, firmware loading, radio test or runtime support
claim follows. Existing Checkpatch metadata limitations remain as documented in
[the integration review](INTEGRATION.md).
