# Combined default/set/full negotiation caller

The [caller draft](tests/mt6797-wmt-negotiate.h) now connects the existing
initial query, fixed mandatory set exchange and full-STP query under a single
attempted lifetime. It is authored code for the future CONSYS member/call site,
not a selected kernel profile or a new boot candidate. The successful
[default-query runtime](../2026-10-03-mt6797-wmt-default-query/results/runtime-2.json)
remains its transport prerequisite.

The shared owner lock must cover the complete call. Persistent storage keeps
the first query, set exchange and full exchange records separately, retaining
clocks and powered resources after every result. The caller stops at the first
failure and preserves the failing phase. Only a checked set event initializes
full-STP sequences to zero and both last ACK values to seven. A 10000–11000-us
sleep follows, preserving the selected source's 10-ms minimum wait with ordinary
scheduler slack; peer transition timing has not been measured. The full query
requires the exact options event, peer credit and completed host ACK through
the existing exchange wrapper. No DLM, patch, calibration or WLAN operation is
selected.

One 1600-ms owner deadline covers phase advancement. Each exchange receives at
most 500 ms clipped to that owner deadline; the first query now accepts an
explicit supplied deadline rather than starting a new 500-ms interval after
clock setup. An already expired supplied deadline refuses before acquiring
clocks or writing registers. Default standalone query behavior remains unchanged
when no deadline is supplied. Framework/scheduler calls are not hard real-time
bounded; every transport remains finitely bounded and late results cannot
advance the negotiation into another phase.

The exact pinned Linux IRQ source confirms that a fresh exclusive
`IRQF_NO_AUTOEN` action resets nested disable depth to one. Shutdown itself
increments depth, so it would be wrong to infer handoff depth solely from the
old query fixture's disable call count. The source hashes and inspected lines
are in the [receipt](results/negotiation-owner.json). This establishes the source
handoff contract, not observed interrupt concurrency.

## Validation and remaining integration

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-10-03-mt6797-wifi-audit/tests/run-wmt-query-transport-test.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-10-03-mt6797-wifi-audit/tests/run-wmt-full-io-test.py
```

The real orchestration is tested with mocked leaf exchanges. Fixtures verify
ordering, first failure, retained records/phase, explicit deadline, expiry at
each boundary, timer wrap, invalid-resource refusal and no repeated lifetime.
The actual initial-query and set/full IRQ/FIFO implementations pass their
separate sanitizer fixtures; both changed headers pass strict kernel style.
These are complementary checks, not a combined real-MMIO test or Linux build.

Next add one logical integration patch for the persistent CONSYS member and
caller, with a separately named diagnostic property and isolated profile.
Preserve canonical series order and the consumed default-query candidate.
Publish clean inputs before the required Buildbox compile, schema and artifact
gates. A device protocol must then admit the extra set/full-mode/ACK effects,
finite budgets, evidence and reviewed recovery before candidate installation.
ROM patch transfer and complete common initialization remain separate work.
