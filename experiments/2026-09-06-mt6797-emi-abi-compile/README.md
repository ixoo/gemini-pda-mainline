# MT6797 EMI ABI compile proposal

This experiment adds the accepted pure EMI argument/result helper as an
out-of-line `emi-abi.o` in the private MT6797 wireless Kbuild directory. The
helper performs only checked arithmetic and low-word signed-result decoding;
there is no runtime caller, secure call, mapping, firmware, registration,
power, DMA, IRQ or hardware path.

The review patch is [0008-wifi-mediatek-compile-emi-abi.patch](0008-wifi-mediatek-compile-emi-abi.patch).
Its generator is deterministic and verifies all frozen predecessor patch
identities before producing the patch. `scripts/verify.py` compiles the exact
implementation as a separate object and links the exhaustive host test under
strict warnings and AddressSanitizer/UndefinedBehaviorSanitizer.

The recorded result is [results/emi-abi-validation.txt](results/emi-abi-validation.txt),
with machine-readable metadata in [proposal.json](proposal.json) and
[validation.json](validation.json). The pinned Checkpatch run and complete
proposal-series replay pass; only the intentionally synthetic missing-DCO and
new-file/MAINTAINERS findings remain. The
[pre-Buildbox integration review](INTEGRATION_REVIEW.md) accepts the exact
shared-series selection. The arm64 Buildbox compile remains pending the clean
pushed integration commit. This is compile evidence only, not Wi-Fi or hardware
support.
