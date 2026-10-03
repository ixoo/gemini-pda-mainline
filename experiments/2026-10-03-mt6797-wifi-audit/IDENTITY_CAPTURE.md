# Mandatory-STP chip-reply capture executor

The [request preparation](IDENTITY_READ_PREPARATION.md) supplies the source-checked
26-byte mandatory-STP chip read. Its response cannot be validated from the
inconsistent vendor event template. The [capture executor](tests/mt6797-wmt-identity-io.h)
now supplies a bounded measurement leaf, with no reply acceptance or continuation.
It is an offline draft without a kernel caller, profile, build or candidate.

## Measurement boundary

The caller must establish a fresh CONSYS lifetime before negotiation or patch
loading, retained BTIF/DMA clocks, DMA exclusion, normal register bank and empty
FIFOs. This leaf makes no clock, DMA, reset, FIFO-clear, resource or power request.
It uses only IER writes, IIR/LSR observations, THR writes and RBR reads. Reuse the
reviewed setup and exclusive resource admission during kernel integration;
preconditions written here are not proof that a caller establishes them.

The only command is the chip read, ordinal zero. The existing bounded TX byte
accounting supplies at most 16 bytes for an empty FIFO or eight for its threshold
state. Each THR byte checks the deadline; partial submission is recorded and
never replayed. TX interrupts are disabled once all 26 bytes have been submitted,
leaving RX enabled. Receiving data before submission completes is a terminal
protocol refusal with no further THR/RBR progress.

The capture has a maximum 500-ms deadline supplied at preparation, 64 services
including the initial kick, 26 THR writes, 32 RBR reads and eight RBR reads per
service. Every received byte remains in persistent owner storage. No inner WMT
length/status parser, event match, ACK, synchronization repair or next command
exists. Initial RX, nonempty TX, unexpected IRQ cause, budget exhaustion and
late submission stop progress. Neither RX length nor content terminates the
capture successfully. Ordinary deadline expiry returns `-ETIMEDOUT`, even when
a full reply was captured; that result names the measurement stop, not identity
acceptance. Classification must inspect exact TX count, raw response and retirement
reason independently, and must never use this return as patch applicability.

The wrapper consumes one attempt before IRQ registration. Registration failure
is terminal without retry or MMIO. It owns `IRQF_NO_AUTOEN`, starts the first
service while the CPU IRQ is disabled, arms once, then joins the handler before
freeing registration or inspecting evidence. All terminal service paths mask
IER; an armed path disables the CPU IRQ once. Acquired clocks and power remain
the caller's retained recovery lifetime. This leaf supplies no cleanup action.

## Focused validation

Run the existing fixture runner:

```sh
python3 experiments/2026-10-03-mt6797-wifi-audit/tests/run-wmt-full-io-test.py
```

The runner now includes the actual capture service and wrapper compiled against
an independent 16-byte FIFO/IRQ model. [Validation](results/identity-capture.json)
passes strict warnings and AddressSanitizer/UndefinedBehaviorSanitizer. It covers
all 256 repeated raw-byte values, deadlines at each of 26 THR and 32 RBR positions,
exact output prefixes and counts, 32/33-byte receive limits, early/stale RX,
nonempty TX, stuck TX and 64-service retirement, expiry during enable, no reply,
expired pre-kick, registration failure, wrong IRQ and consumed-attempt refusal.
Every registered path checks balanced disable depth, synchronization and freeing;
terminal and second-call paths make no further FIFO progress. The existing
full-STP and negotiation fixtures also pass.

These fixtures do not prove real FIFO thresholds, actual IRQ ordering, transport
setup, timer behavior or the chip's reply encoding. Before build/deployment,
integrate the leaf into a separate default-off CONSYS selector, preserve exact
raw-byte and terminal records, validate the actual caller's pretrigger/resource
and recovery gates, then use Buildbox and the guarded boot2 path. A new capture
must stop before HW/ROM reads, negotiation, firmware patch, PA/calibration, WLAN
or scan. Its sole decision-changing observation is the pre-patch chip reply
framing/header/status/address/value; firmware selection remains a later checked
owner step. Working Wi-Fi still requires calibration, management reception,
association and traffic.
