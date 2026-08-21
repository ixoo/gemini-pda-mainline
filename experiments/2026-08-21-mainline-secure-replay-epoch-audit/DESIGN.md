# Secure replay epoch authority boundary

## Proven initialization chain

For the named Gemini revision, the private A72 replay byte has an explicit
initialization owner:

```text
regular preloader boot
  -> authenticated tee1 load, tee2 fallback
  -> exact duplicate secure payload
  -> primary BL31 entry
  -> zero [0x11d340, 0x122acc)
  -> replay byte 0x11ea24 is zero
  -> A26 prevents the only pre-A34 set path
```

The zero helper performs stores; this is not an inference from zero padding.
Its first range covers the complete secure BSS containing the ledger. The
result also does not depend on the separately preserved ATF log buffer.

## A34 ownership rule

The future production owner may assign
`MT6797_A72_A34_PRIVATE_REPLAY_OWNER_SAFE_ZERO` only when all of these are
true:

- the named board selects the exact audited preloader/BL31 firmware contract;
- separate reset provenance establishes a platform or external reset whose
  successful boot path reaches primary BL31 entry;
- A26 has prevented CPU8 and CPU9 `CPU_ON` before publication;
- the complete writer inventory remains unchanged; and
- the immutable Linux topology, P30, provider, membership, transaction,
  fault, generation, and cookie tuple is revalidated immediately before the
  one lifecycle transition.

The private replay value supplied to the evaluator remains exactly zero. A
static default, omitted field, Linux BSS value, or caller assertion is not a
proof.

## Remaining reset-provenance boundary

This audit does not convert an ordinary Linux reboot into
`MT6797_A72_A34_RESET_PLATFORM`. The next audit must determine which exact
TOPRGU and validated current-preloader observations prove all of the following:

1. reset reached the regular preloader boot path;
2. primary BL31 entry ran in the current boot;
3. the reset class is strong enough to recover every A34-owned hardware and
   cross-owner prefix, not only the replay byte; and
4. no unknown or contradictory bit pattern is accepted.

The classifier must consume immutable typed snapshots. It must not reread
MMIO, remap retained RAM, parse physical memory directly, or combine
correlated fields into a success result without source-backed semantics.

## Rejected inputs

- ATF log content, sequence, validity, or crash flags;
- raw TOPRGU status alone;
- retained preloader status alone;
- LK boot reason or completion alone;
- a manually described cold-looking display sequence;
- Linux zero initialization;
- active PSCI `AFFINITY_INFO`;
- a successful ordinary reboot; or
- a board-agnostic unconditional firmware claim.

## Implementation order

1. Freeze the strict platform/external reset classifier and its reject table.
2. Implement and prove that classifier without a production A34 caller.
3. Audit the atomic A34 tuple collector/publication owner against the now
   separate reset and replay proofs.
4. Only after that owner opens, prepare one CPU8 request with the existing
   P30, timeout, rollback, and fail-stop contracts. CPU9 stays vetoed.

No code, build, boot image, device write, CPU request, or hardware action is
selected by this audit.
