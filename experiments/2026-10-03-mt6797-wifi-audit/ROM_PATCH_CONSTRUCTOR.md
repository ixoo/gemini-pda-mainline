# Strict retained-pair parsing and fragment construction

The [constructor](tests/wmt-rom-patch.h) implements the bounded input checks
needed by [the retained patch-order review](ROM_PATCH_ORDER.md). It has no file
loader, firmware authentication, hardware caller or transport effects. The
selected loader's inconsistent short-read checks and the kernel downloader's
header subtraction are reasons to validate complete sizes before arithmetic.

## Selected input and construction contract

The parser accepts the selected two-file pair only. The caller supplies expected
sequence 1 or 2 after verifying the complete pinned software digest separately.
It requires exact file size, 28-byte header, patch count 2, matching sequence and
address metadata. Sequence 1 requires a 46444-byte body and wire address
`00 00 0a f0`; sequence 2 requires a 210876-byte body and `00 00 09 00`.
The returned view aliases immutable input and omits the header from transfer.
No lexical filename ordering or filesystem enumeration chooses the sequence.
Metadata alone does not authenticate the body or prove hardware applicability.

Each fragment payload is five command bytes followed by at most 1000 body bytes.
Command type/opcode are `01 01`; its little-endian length counts flag plus body.
Flags are first 1, middle 2 and last 3; the last-fragment rule takes precedence
for a one-fragment body. Checked bounds precede index multiplication and output
mutation. Construction uses a separate output buffer and preserves input bytes;
it does not reuse the vendor's overwrite of the previous fragment tail.
Refused metadata and fragment requests leave their outputs unchanged.

This helper constructs one payload, not an ordered transfer. The future owner
must obtain the exact firmware through the reviewed standard interface, verify
identity and live hardware/ROM-version selection, complete both address exchanges,
then advance fragment index only after checked STP state and the exact five-byte
patch event. Each completed patch still requires its ordinary WMT reset.
No address exchange, reset or calibration is admitted here. Addresses remain
firmware wire fields, not AP MMIO ranges.

## Validation

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/2026-10-03-mt6797-wifi-audit/tests/wmt-rom-patch-test.c \
  -o /tmp/gemini-rom-patch-test
/tmp/gemini-rom-patch-test
rm /tmp/gemini-rom-patch-test
```

Synthetic tests cover all 258 fragments, first/middle/last flags, exact length
fields, final body lengths 444 and 876, body coverage, full-STP encoding, short
files, wrong sequence/count/address, capacity refusal, out-of-range indices and
a one-fragment synthetic body. Strict warnings and address/undefined behavior
sanitizers pass. Inputs contain no retained firmware bytes.

A separate native test in the project RE VM verified both retained files against
their selected corpus-manifest digests before parsing, constructed every body
fragment with byte-for-byte comparison, refused one-byte truncation and reversed
sequence, and rechecked input hashes afterward. It compiled only independently
authored validation code; firmware and the vendor loader were not executed.
Managed temporary compile files were removed. The
[receipt](results/rom-patch-constructor.json) pins code and retained input hashes;
raw firmware and the private RE script stay outside Git.

There is no installed-file attribution, new chip-version selection, Linux
integration, device exchange, RF calibration or Wi-Fi claim. First
[default-query liveness](../2026-10-03-mt6797-wmt-default-query/SESSION.md) and
[the common-init contracts](COMMON_INIT_REVIEW.md) still precede a candidate.
