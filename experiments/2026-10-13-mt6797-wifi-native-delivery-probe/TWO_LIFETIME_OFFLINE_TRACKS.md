# Two-lifetime offline tracks — negative result recorded

Track B is now **NEGATIVE**; see the [evidence and firmware-restart pivot](FIRMWARE_RESTART_BOUNDARY.md). The earlier pending table below is retained as history. No credit/drain-based protected reuse is admitted.

Owner direction, 2026-10-23: accept the
[incomplete attribution checkpoint](TWO_LIFETIME_PREDECLARATION.md), implement
only dormant host prerequisites, and await the owner's firmware evidence.
No build, firmware command, sampler, admission change, installation or boot.
The one-boot allowance remains unconsumed. P2E-D1/D2 remain consumed.

## Track A: unconsumed host helpers

Proposals 0229 and 0230 follow 0228 in canonical order and in the snapshot
compile profile. `CONFIG_MT6797_CCMP_LIFETIME_PREREQUISITES` defaults to `n` and
is not enabled by any profile. No re-arm, RX or command path consumes either
helper. The MAC differs only by two includes; its admission behavior is
unchanged. These are prerequisite interfaces, not a second-lifetime capability.

`mt6797_lifetime_drain_fence()` evaluates supplied observations once. It
requires an empty RX queue, no pending records, a whole ledger, no outstanding
card/command credit or pending CPU/FFA, and a matched round-trip reply. The
round-trip must have been issued after final teardown completion, and its
reply must have established prefix-processing semantics. A matching reply
alone cannot set that proof input. The command family and its semantics are
not selected here, and the helper issues no command.

The supplied quiet-window record count must cover **every** RX record after
the reply, not just deliverable data or the queue's final size. It must be zero
through a 100–200 ms bounded interval. This is a host drain condition, not a
heuristic proof that a delayed event or timer cannot fire. All inputs and the
pass/refusal are logged. The fence object is consumed even on failure; a later
call on that object always refuses. It must persist for the retirement attempt,
not be reset to retry. A host-fence pass does not change admission or establish
firmware retirement while Track B is unknown.

The PN helper owns one context per `(opaque key identity, key index, peer,
generation)`, including PTK/GTK role. A new key uses separate pristine storage;
a live or retired context cannot be overwritten. PTK starts at the handshake
RX sequence. GTK remains unseeded until its first accepted frame. Both require
explicit activation before RX. Equal/lower PN and mismatched ownership refuse
without changing the context. Stage 3 has no PN-reset interface. Retirement
requires proven producer retirement and preserves the old floor.

Descriptor ownership must have independent provenance. An untagged raw RXD
cannot be relabelled with the current owner: `provenance_proven=false` refuses
even a higher PN. The old-owner/higher-PN fixture uses an explicitly attributed
host record and verifies the owner mismatch; it does not claim that raw firmware
RXDs have gained a generation field. The earlier raw-descriptor counterexample
still stands until Track B resolves.

Actual-header fixtures exercise quiet-window records, each credit/queue/pending
condition, reply ordering/proof, finite quiet bounds, terminal refusal, all owner
fields, inactive RX, equal/lower PN, old-owner higher PN, fresh-key low PN, GTK
first-frame seeding and all four GTK indices. They run with ASan/UBSan. The
option-off headers preprocess to nothing, and the MAC is byte-identical to the
0228 parent after removing the two includes. No complete kernel was rebuilt.

Reproduce the focused test against an exactly replayed source tree:

```sh
python3 tests/lifetime-prerequisites-test.py <0230-tree> <0228-mac.c>
```

## Track B: owner-produced firmware evidence — required work list

The owner is producing the private firmware evidence. Do not infer these
answers from a host generation, returned credit, queue snapshot, quiet delay,
management-frame release or successful traffic. No device experiment is selected
to answer them. For each row, evidence must establish causal ordering relative
to the **credit that releases that command**, including delegated callbacks,
deferred work and error paths, rather than only the handler's visible return.
Record exact firmware identity and supporting locations privately; publish only
sanitized conclusions with permission.

| Handler | Event emitted synchronously before return and before releasing credit? | Beacon-loss timer cancelled? | Aging timer cancelled? | Station/BSS queues flushed? | Evidence status |
| --- | --- | --- | --- | --- | --- |
| `0x07` key operation | NO: key events observed after released-page credit | UNKNOWN | UNKNOWN | UNKNOWN | Negative runtime ordering; owner static support |
| `0x14` station removal | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Owner evidence pending |
| `0x11` BSS operation | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Owner evidence pending |
| `0x17` abort indication | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Owner evidence pending |

A justified not-applicable entry must explain which other teardown operation
owns that producer, timer or queue and where its terminal boundary is proven.
Unknown fields keep the decision pending. Management-class release alone says
nothing about data queues. No positive firmware guarantee is introduced by
Track A's interfaces or synthetic tests.

## Decision branches — recorded before any further candidate work

- **Events synchronous before the releasing credit**, with the table's timer
  cancellation and queue-retirement obligations resolved: the drain fence plus
  the whole ledger is the barrier. Then, and only then, prepare the two-lifetime
  candidate and its actual admission/host fixtures. A rebuild including 0228 is
  still mandatory; none is authorized while this decision is pending.
- **Any event emitted after releasing credit, or timers not cancelled:** second
  protected lifetime is unsupported. Record reconnect as blocked on a firmware
  capability we cannot add, retain the one-lifetime driver and stop. Do not
  substitute a timing heuristic, longer delay or host generation label.

The negative branch has resolved. Same-firmware protected reconnect is blocked
on a firmware capability we cannot add; re-arm stays refused. The separate
firmware-restart inventory is held on UNKNOWN prerequisites. The one-boot
allowance remains unconsumed; no physical boot2 handoff is pending.
