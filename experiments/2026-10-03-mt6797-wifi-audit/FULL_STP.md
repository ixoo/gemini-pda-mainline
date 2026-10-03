# Full-STP framing for the common-init follow-up

The [codec](tests/wmt-full-stp.h) is an independently written, hardware-free
WMT subset. It encodes data and header-only ACKs and validates one complete
frame. It is not connected to BTIF or selected by a kernel profile. The
[first default query](../2026-10-03-mt6797-wmt-default-query/SESSION.md) remains
the hardware gate before further transport effects.

## Source contract

The retained selected Gemian source defines full-mode data framing as four
header bytes, payload and two CRC bytes. Header byte zero carries sync bits
`10`, a three-bit sequence and three-bit acknowledgement. Byte one carries
task index and the upper four payload-length bits; byte two carries the lower
length bits. Byte three is the low byte of the first three bytes' sum. WMT
uses task index 4. The payload CRC is reflected CRC-16 polynomial `0x8005`,
initial value zero, transmitted low byte first. ACKs have zero length and
four header bytes only; they carry no CRC.

The codec limits payloads to 1005 bytes: a five-byte patch command header and
1000-byte fragment. This is a selected command bound, not the general STP
limit. It rejects NAK, other tasks, malformed checksums, partial and concatenated
frames. Delimiters, resynchronization, diagnostic channels and retransmission
are outside this subset. The retained source's static NAK and delimiter flags
are zero; comments about NAK polarity conflict with executable branches, so
this review uses the branches. Peer behavior has not been observed.

The source initializes transmit sequence to 0, last transmitted ACK and last
received ACK to 7, expected receive sequence to 0 and window credit to 7.
Sending consumes credit and advances sequence modulo eight. Received ACKs
restore credit only within the outstanding transmit window. Ordered received
data advances receive sequence and causes an ACK. A valid codec result does
not prove that a frame belongs to that window, epoch or expected WMT exchange.
The caller must retain the input buffer while using the decoded payload.

Upstream Bluetooth UART framing with unused checksum/trailer fields cannot be
assumed to supply this selected full-mode sequence/ACK/CRC contract unchanged.

The selected Gemian parser differs from the earlier vendor copy: explicit
braces keep task/length parsing outside the NAK-enabled branch. The earlier
copy would skip that processing when NAK is disabled. The receipt pins the
selected prepared source; byte equivalence to that earlier copy is not claimed.

## Focused verification

Run from the repository root, keeping the binary outside the checkout:

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  experiments/2026-10-03-mt6797-wifi-audit/tests/wmt-full-stp-test.c \
  -o /tmp/gemini-wmt-full-stp-test
/tmp/gemini-wmt-full-stp-test
rm /tmp/gemini-wmt-full-stp-test
```

The [tests](tests/wmt-full-stp-test.c) check independently evaluated OSAL-table
CRC vectors, golden query/reply frames, all single-bit corruptions of the reply,
every reply truncation, trailing bytes, all sequence/ACK encodings, header-only
ACKs, the maximum selected payload, unsupported tasks/flags, oversized lengths
and invalid arguments. Sanitizers and strict compiler warnings pass. Round trips
prove encoding consistency; they do not independently prove firmware acceptance.

## Remaining integration decisions

Before composing [common initialization](COMMON_INIT_REVIEW.md), resolve the
mandatory-to-full-mode transition, peer ACK ordering, reset epochs after each
patch, bounded FIFO transmission/IRQ progress, exact event matching and finite
time/effect budgets. Do not advance state on a syntactically valid but unexpected
frame. Define the powered failure lifetime before transferring any private ROM
patch or issuing calibration. No kernel build, hardware exchange, calibration
or Wi-Fi support is established by these host tests.

The [receipt](results/full-stp-codec.json) pins source and authored file digests.
Raw vendor source and private inputs remain outside Git.

The [state follow-up](FULL_STP_STATE.md) now traces the full-mode boundary and
per-patch WMT reset distinction and tests a one-command window. Peer timing,
FIFO/IRQ integration and device admission remain separate.
