# Gemini retained transition-ledger contract

## Ownership and location

The owner is a default-off, built-in pstore component for the Planet Gemini
PDA. It uses only the first 4 KiB dmesg zone at `0x44410000`, inside the exact
already-qualified `[0x44410000,0x444f0000)` retained reservation. Normal
ramoops registration is bypassed on the Gemini only while this isolated owner
is selected. The existing fixed protected-readback ledger remains unchanged
and is mutually exclusive.

The physical API has no caller in this milestone. A later CPU8 binder must
claim it with one nonzero attempt identity before the executor's first
checkpoint. There is no release or reset API in the same boot.

## Compact wire record

The normal 12-byte persistent-RAM header remains at the start of the zone. Its
payload is exactly two alternating nine-word records (72 bytes total). Each
record contains:

1. ledger magic;
2. version and word count;
3. attempt identity low word;
4. attempt identity high word;
5. monotonically increasing generation;
6. phase;
7. stage;
8. terminal class; and
9. CRC32 integrity word.

The two copies are not two stage records. They form one mutable last-stage
ledger: every checkpoint replaces the older copy while preserving the newest
valid copy until the replacement is complete. This bounds retained storage to
one 4 KiB zone rather than allocating 18 independent ramoops records.

## Update protocol

The owner accepts only an exact empty persistent header, an all-ones raw
header previously qualified by the first-dmesg work, or an exact 72-byte
ledger header with at least one valid copy. Any other header or an ambiguous
equal-generation pair is rejected before a write.

For every update it:

1. invalidates only the older copy's integrity word;
2. orders that invalidation;
3. writes the eight payload words;
4. orders the payload;
5. commits the CRC32 word last;
6. orders and reads back the complete copy; and
7. on the first update only, commits persistent start, size, and if needed the
   `DBGC` signature in that order, with complete header readback.

A mismatch seals the owner and permits no retry. The other copy therefore
retains the last completely committed checkpoint. Generation wrap is refused.

## Sequence contract

Phases are `before`, `after`, and `terminal`; stages are the executor's nine
physical stages, numbered 1 through 9. The first record must be `before:1`.
An `after` must match its preceding `before`; the next `before` must advance
exactly one stage. A terminal record may follow the last before or after and
must carry a nonzero executor terminal class. Nonterminal records must carry
terminal zero.

Foreign attempt identities, stage skips, phase inversions, post-terminal
updates, and a second begin are rejected without writes. Entry rejections
remain checkpoint-free; the later binder must perform the executor's entry
preflight before claiming the physical ledger.

## Hardware-free proof

The focused KUnit suite calls only the internal owner with an injected word
array and barrier counter. It covers all 18 ordered before/after checkpoints
plus the terminal record, raw-header signature-last commit, malformed and
foreign-input refusal, a torn replacement that preserves the prior copy,
recovery from one corrupt copy, and terminal one-shot sealing.

QEMU contains the physical mapping code but no production caller. Therefore
the proof performs no retained-RAM access, MMIO, watchdog action, SMC, CPU
request, device access, or boot-candidate construction.
