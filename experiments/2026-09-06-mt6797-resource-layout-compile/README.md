# MT6797 reserved-resource layout compile proposal

This experiment adds a separately compiled private `resource-layout.o` that
composes the initialized `mt6797_image_reserved_info` into the fixed first-MiB
WLAN and WMT ranges, calls the predecessor checked common-remap encoder, and
describes EMI regions 18 and 19. It selects no permission policy and performs
no MMIO, mapping, locking, registration, probe, firmware, DMA, IRQ, power,
reset, or runtime admission effect. The predecessor active binding refusal is
unchanged.

The generated local proposal is
[`0010-wifi-mediatek-compile-resource-layout.patch`](0010-wifi-mediatek-compile-resource-layout.patch).
The verifier records its exact identity, frozen 12-entry series inventory,
evidence hashes, strict host fixture result, and expected Checkpatch findings.
Run `python3 scripts/verify.py` to reproduce the result. The host fixture
covers valid minimum/larger resources, SET at zero, CLEAR at its representable
lower boundary, highest first-MiB base, 1 MiB-only alignment, exact CLEAR/SET
selectors, all interval mismatches, zero-generation and extent refusals,
explicit start/end ordering, selector and first-MiB overflow, invalid
selectors, identical-object refusal before input access, cleared outputs, and
null output.

Exact Linux-series replay and Buildbox compilation remain integrator-owned.
The input record is descriptive initialized state, not a reservation,
exclusion, selector-provenance, or resource-ownership grant. Partial byte
overlap is a caller precondition and is intentionally not detected. Equality
of a supplied selector or expected state does not exclude external writers.
