# Pure fixed-port HIF command encoder

[`hif_command.h`](src/hif_command.h) implements the known command fields
established by [the PIO audit](PIO_COMPLETION.md), using its
[pinned source ledger](results/pio-sources.json). The earlier negative
completion finding is preserved: it gates runtime transfer-engine admission,
not this independent arithmetic component. No completion bit or MMIO API is
added.

`mt6797_hif_encode_command(port, direction, policy, payload_bytes, capacity,
result)` returns a native numeric command word and padded transfer length.
It reuses the accepted sizing helper without changing it. Only write WTDR1
(`0x34`) and read WRDR0/1 (`0x50/0x54`) are admitted. Other register ports,
including WHISR, are outside this command/response component. Function 1 and
fixed-port mode are constants; no arbitrary function or increment mode is
accepted. Direction and policy enums, the 17-bit port width, allowed
direction/port pairs and nonzero nine-bit count are checked before encoding.

`PIO_ONLY` means source `use_dma=0`: RX and TX use four-byte rounding.
`DMA_ENABLED` means source `use_dma=1`: response-port RX uses eight-byte
rounding in byte mode even if the eventual engine falls back to PIO. TX
sizing is identical under both policies. Policy does not select an engine,
map a buffer or establish DMA translation. The helper's existing false
receive branch supplies four-byte PIO-only RX rounding; its `dma_bytes`
output is exposed here under the engine-neutral name `transfer_bytes`.
Block selection still occurs after initial four-byte rounding, with 512-byte
blocks and at most 511 blocks. DMA-enabled RX sizes 505–508 remain refused
because their byte-mode count would become 512; PIO-only RX accepts them
with 508 padded bytes. No zero-count special meaning or silent split is used.

The result is cleared on every failure when an output pointer exists.
Invalid fields return `-EINVAL`; invalid lengths/capacity return
`-EMSGSIZE`. No payload bytes or addresses are accessed. The caller must
provide initialized TX padding and sufficient RX storage, then apply the
appropriate register-write API to the numeric word only after independent
runtime admission. The word is not a serialized packet or DMA descriptor.
The header follows the existing helper's host/Linux include convention;
kernel integration has not been compiled or installed.

The [29 explicit fixtures](src/hif_command_test.c) use literal expected
words for both directions, both RX ports, both policies, byte/block
boundaries and maximum count. Refusals cover zero/overflow lengths, padded
capacity, direction/port mismatch, out-of-width ports, invalid enums,
ambiguous count 512 and NULL output. They check cleared output on failures.
The earlier 30 sizing fixtures also pass. Both executables were built with
strict C11 warnings, AddressSanitizer and UndefinedBehaviorSanitizer and
removed from their managed temporary directory after execution.

Integration still requires proven owner/firmware state, serialization,
resource/credit admission, initialized buffers, response attribution and
bounded completion/error recovery. DMA additionally requires the unresolved
address translation and channel lifetime contract. This component supplies
neither active driver readiness nor a device/backend action. Prior handoffs
and shared kernel/planning files are unchanged.
