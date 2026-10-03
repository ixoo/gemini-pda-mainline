# Pre-negotiation identity reads: request preparation

The [installed ROM review](ROM_APPLICABILITY.md) establishes the installed
pair and the pinned source's chip/HW/ROM-before-negotiation order. The
[request helper](tests/wmt-identity-read.h) now constructs only those three
mandatory-STP read frames. It accepts an ordinal, not a caller-selected address
or operation; invalid ordinal, absent output and insufficient capacity refuse
without writing any output. All HW/ROM input-value bytes are initialized to
zero, eliminating the vendor caller's uninitialized request bytes.

[Focused validation](results/identity-read-preparation.json) passed strict C11
warnings, AddressSanitizer/UndefinedBehaviorSanitizer, all three decoded request
fields, output guards and 29 refusal cases. Independent comparison against the
hash-pinned vendor command array, register definitions and mandatory-STP framing
matched all three complete frames. No reply parser, transport execution or
chip/patch applicability decision is implemented by this helper.

Reproduce the host-only fixture from the repository root:

```sh
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cc -std=c11 -Wall -Wextra -Werror -Wconversion -Wshadow -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  experiments/2026-10-03-mt6797-wifi-audit/tests/wmt-identity-read-test.c \
  -o "$work/test"
"$work/test"
```

## Why a reply capture is still needed

A bounded RE-VM search of both hash-pinned retained patch bodies found neither
complete candidate register-read event prefix: the source template with length
four, or the structurally consistent length-twelve alternative. Opcode-only
matches are not protocol evidence. Furthermore, version reads precede patch
loading in the selected source, so those patch bytes cannot establish the
pre-patch ROM handler. The existing retained Gemian boot log reports selection
but contains no attributable raw register reply. Do not select either event
encoding from these negative results.

A distinct capture-only diagnostic is the next useful hardware measurement:
construct the chip read at firmware address `0x80000008`, preserve its complete
bounded response, and stop with power/clocks retained. It must not accept the
inner WMT length/status as successful applicability or proceed to the HW/ROM
reads, negotiation, patch, PA, calibration, WLAN or scan. This measures the
unknown event format before a strict selector is integrated. Further reads in
a complete owner advance only after their own checked responses.

The request is 26 bytes, larger than the previous fixed-query and set-options
paths' 16-byte FIFO assumption. A capture executor therefore needs reviewed TX
FIFO progress and interrupt retirement, not a widened initial burst. Reuse the
proved bounded-service approach from the full-STP executor while preserving
mandatory framing. Record a finite whole deadline, THR/RBR/service budgets,
pretrigger gates, exact raw-byte storage and terminal failure behavior before
kernel integration. Do not reuse a full-mode parser or infer receive encoding
from an inner vendor template. No automatic resynchronization, retries, FIFO
flush, DMA or cleanup power-off belongs in this measurement.

This is preparation, not an admitted runtime protocol. The kernel executor,
fixtures of its actual IRQ/FIFO path, default-off selector, Buildbox build,
validated candidate, guarded deployment and attributable capture remain to do.
It does not change the Wi-Fi support claim or establish calibration/reception.
