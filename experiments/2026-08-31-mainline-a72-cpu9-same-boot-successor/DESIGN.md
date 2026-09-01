# Frozen same-boot CPU9 successor contract

## Immutable parent

The parent is exact patchset `dd072599...` from repository build commit
`aa2efd3f...`. Its CPU8-only transition and two successful runtime records are
the baseline. The successor must preserve the existing CPU8 stage order,
callbacks, terminal values, record-0 wire format, one-request bound, and
failure behavior.

## Admission boundary

One userspace trigger may perform this sequence once:

1. run the unchanged CPU8 admission path;
2. require CPU8 transition lifecycle `TERMINAL`, terminal
   `CPU8_ONLINE_PROOF`, membership published, retained mask `0x7`, provider and
   P27 still owned, CPU8 online, and CPU9 offline;
3. derive and publish one CPU9 transaction from the owner-local post-CPU8
   state and the existing exact READY token;
4. issue exactly one `add_cpu(9)` request;
5. complete CPU9 P30E, standard PSCI CPU_ON, generic secondary-online, one
   synchronous IPI, and membership publication; and
6. expose the combined terminal state before the inherited watchdog recovers
   the device.

CPU9 is never issued when CPU8 returns an error or any CPU8 proof field is
missing. The trigger, CPU8 attempt, and CPU9 attempt are each one-shot; no
retry API or loop exists.

## Owner state

The CPU9 transaction requires all of the following under the existing A72
transition serialization:

- owner health `AVAILABLE` and phase `IDLE`;
- members exactly `BIT(0)`;
- a valid held provider identity;
- CPU8 retired success present and CPU8 success publication set;
- CPU8 online, CPU9 offline, and both targets possible/present with MPIDRs
  `0x200` and `0x201`;
- the CPU9 attempt available and not consumed; and
- the parent binder's exact CPU8 terminal/DCM proof.

The CPU9 transaction inherits the held provider identity and receives only a
CPU_ON budget. Preparation, provider-acquire, provider-abort, P28, P29, and
CPU_OFF budgets remain absent.

Add CPU9-specific production preflight, claim, reject, begin-CPU_ON,
publish-success, and finalize-success entry points. Do not weaken or
parameterize the proven CPU8 wrappers merely to make CPU9 pass.

## CPU9 executor

Use a separate controller and result structure. Its ordered stages are:

1. `PRESTATE`: validate the complete post-CPU8 proof and open the CPU9 ledger;
2. `CPU_ON`: prepare/arm the existing CPU9 P30E slot and call standard PSCI
   once;
3. `ONLINE_WAIT`: require CPU8 and CPU9 both online after generic secondary
   completion;
4. `IPI`: complete one synchronous call on CPU9; and
5. `MEMBERSHIP`: publish and finalize members `BIT(0) | BIT(1)`.

The executor has no callbacks for watchdog, P27, provider acquire/release,
isolation, SRAM, DCM, CPU_OFF, or retry. Those absences are structural and
must be checked in source and linked-call inventories.

Every failure after CPU8 success is terminal and retains CPU8, the provider,
and cluster state until watchdog recovery. A CPU9 `cpu_up` rollback still
publishes and consumes the existing generic P32 evidence after the CPU9 binder
records its own terminal. No inverse cluster action is introduced.

## Durable evidence

Record 0 at `0x44410000` remains the byte-compatible CPU8 transition ledger.
Record 1 at `0x44411000` becomes a separate CPU9 transition ledger. It reuses
the proven magic/version and two-copy CRC wire format so the existing parser
can validate both records, but has independent physical ownership, attempt
binding, stage vocabulary, and terminal seal.

Before mapping record 1 for write, the CPU9 ledger must:

- verify the exact Gemini model and the existing `0x44410000`/`0xe0000`
  no-map ramoops reservation with 4 KiB records;
- read record 0 only;
- require its existing 72-byte header and two-copy format;
- require the latest CRC-valid record to be terminal stage `MEMBERSHIP` with
  terminal `CPU8_ONLINE_PROOF`; and
- reject any nonempty, malformed, already committed, or previously attempted
  record 1.

The CPU9 lane records only its five executor stages and one terminal. It never
clears, repairs, retries, or overwrites a committed CPU9 lane. Gemian recovery
must expose both `dmesg-ramoops-0` and `dmesg-ramoops-1`; the runtime classifier
requires the CPU8 terminal in record 0 and the CPU9 terminal in record 1.

## Pre-ledger progress diagnostic

The sole corrected device attempt proved the exact CPU8 terminal in record 0
while record 1 remained logical-empty. A successor diagnostic therefore owns
only the already-empty record at `0x44412000..0x44412fff`. It does not change
record 0 at `0x44410000` or the CPU9 transition lane at `0x44411000`.

Before its first write, the progress owner must validate the exact Gemini
model, the existing `0x44410000`/`0xe0000` no-map ramoops reservation and 4 KiB
record size, the CRC-valid CPU8 terminal stage 10/terminal 5 bound to the
caller-supplied CPU8 attempt, and the exact logical-empty `DBGC/0/0` progress
header. Raw, malformed, torn, or committed progress predecessors are refused.
The legacy CPU8 admission trace must be disabled in the diagnostic profile
because its historical two-record ownership overlaps the CPU9 and progress
lanes.

The progress payload is the existing 72-byte two-copy ledger format. Each
36-byte little-endian copy contains magic `0x4c543747`, version `0x00010009`,
the low and high CPU8-attempt words, generation, phase, stage, terminal, and
CRC32 over the first eight words. The owner commits `BEFORE` and `AFTER` for
each completed boundary:

1. exact CPU8 proof and progress ownership;
2. ready token;
3. CPU9 derivation;
4. CPU9 publication;
5. CPU9 binder preparation;
6. `add_cpu(9)` dispatch intent;
7. CPU9 binder entry;
8. CPU9 ledger-begin entry;
9. successful CPU9 ledger-begin return; and
10. `add_cpu(9)` return.

The maximum is 20 record commits and 202 32-bit writes within that one record.
Each record is CRC-last with a full barrier and full ordered readback; the
header length and size are committed only after the first valid copy. The
writer alternates its two owned copies during the one attempt, never clears or
repairs the lane, never retries a failed commit, and seals after stage 10 or
any production error. It performs no pre-DT access and no CPU, CPU_OFF,
watchdog, regulator, clock, I2C, firmware, reset, reboot, storage, or power
operation. Gemian recovery reads the pstore file and exact physical header;
the source-pinned recovery classifier accepts only CRC-valid monotonic copies
and names the last complete boundary.

## Success predicate

The first device attempt passes only when all of these agree:

- exact candidate identity and fresh boot ID;
- pristine zero-execution trigger state;
- one CPU8 request and one CPU9 request, with no other CPU request;
- CPU8 terminal `CPU8_ONLINE_PROOF` and CPU9 terminal
  `CPU9_ONLINE_PROOF`, both with zero stage/checkpoint error;
- CPU mask `0-9` and advancing accounting for both A72 CPUs in one bounded
  read-only interval;
- zero CPU_OFF, retry, native reboot, partition read, or storage write; and
- changed-ID Gemian recovery with two CRC-valid terminal ledgers.

An error, missing terminal, missing accounting advance, malformed lane, or
premature recovery is a stop-and-classify result. It never authorizes a retry
in the same boot.

## Logical implementation patches

1. Add the guarded independent CPU9 ramoops-record ledger and focused tests.
2. Add owner-local CPU9 derivation and CPU9-specific membership lifecycle
   entry points with focused tests.
3. Add the hardware-free retained-cluster CPU9 executor and failure tests.
4. Bind CPU9 P30E/PSCI/completion/failure dispatch without changing CPU8
   behavior.
5. Chain CPU9 after exact CPU8 proof in the candidate-only controller and add
   combined diagnostics and no-network tests.

Each patch is experiment-only until actual authorship and upstream ownership
are established. Synthetic archive metadata must not carry a DCO sign-off.

## Validation gates

- deterministic generation and reversal against the exact parent;
- strict patch review and changed-call inventory;
- focused KUnit coverage for both success and every precondition/failure
  branch;
- mutations that attempt CPU9 before CPU8 proof, replay any cluster effect,
  arm/refresh watchdog, add CPU_OFF or retry, write record 1 without record-0
  proof, overwrite either lane, or accept a missing terminal;
- exact Buildbox builds of the CPU8 parent, focused successor tests, and the
  production successor profile;
- unchanged CPU8 configuration/call graph outside declared dispatch additions;
- two independent Android-v0 constructions, full LK/container validation, and
  negative mutations; and
- a predeployment decision map before the sole first device attempt.
