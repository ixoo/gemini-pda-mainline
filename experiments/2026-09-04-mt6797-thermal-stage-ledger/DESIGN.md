# MT6797 thermal-stage retained ledger design

## Decision boundary

The first thermal-serviceability boot returned to Gemian before the exact USB
transport appeared and left pstore empty.  Record 5 at physical `0x44415000`
was independently recovered in pstore-empty state.  Repeating that candidate
cannot distinguish boot selection, thermal probe entry, or a particular
thermal transaction boundary.

The derivative in this experiment changes only observation.  A default-off
owner records the latest completed or entered MT6797 thermal probe operation in
record 5.  It does not change the reset, clock, AUXADC, APMIXED, bank, sample,
zone, CPU, frequency, load, idle, suspend, trip, cooling, or reboot policy.

## Wire contract

- Exact reservation: `0x44410000..0x444effff`, 4 KiB ramoops records.
- Exact owned record: record 5, `0x44415000..0x44415fff`.
- Accepted predecessor: raw-empty or pstore-empty only.
- Three ramoops header words remain untouched until the first CRC-valid copy
  has passed a complete readback.
- Two alternating 12-word copies contain magic, version, generation,
  operation, phase, bank index, signed result, terminal kind, a fixed attempt
  identity, and CRC32.
- Each commit invalidates the destination CRC, writes data, publishes CRC last,
  performs ordering barriers, and requires exact readback.
- The owner never clears, repairs, resumes, reopens, or retries a nonempty
  lane.  A terminal seals it.
- The fixed successful path is bounded to 84 commits and 1,095 32-bit writes;
  the implementation admits at most 96 commits.

## Instrumentation contract

The existing ordered transaction gains one optional trace callback.  With no
callback, its hardware operation order and cleanup are unchanged.  With the
isolated ledger profile, every forward operation is recorded immediately
before it and immediately after its return; cleanup is deliberately untraced
so it cannot obscure the causal forward boundary.  A trace failure before an
operation prevents that operation and enters the existing cleanup path.

Probe-level checkpoints cover probe entry, calibration, resource mapping,
AUXADC and APMIXED mapping, reset and clock acquisition, the complete ordered
transaction, thermal-zone registration, explicit failure, and successful
probe completion.  Per-bank transaction checkpoints carry bank indices 0--5.

## Result map

- Empty record after a changed boot cycle: thermal probe did not own the lane;
  investigate boot selection or entry before this driver.
- CRC-valid `BEFORE`: the named operation was entered but did not return.
- CRC-valid `AFTER` with an error: the named operation returned that error.
- Failure terminal: the probe returned after the recorded boundary.
- Success terminal: the zone registered and the probe completed; proceed to a
  read-only runtime temperature/serviceability frame.
- Malformed or nonempty predecessor: ownership refusal; do not interpret it as
  a thermal result.
