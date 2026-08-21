# Strict retained ram-console parser boundary

## Selected boundary

The only implementation selected by this audit is:

```text
caller-owned immutable byte buffer -> strict prefix validation -> raw status
```

It is a wire-format parser, not a physical-memory reader. It cannot map the
Gemini reservation, classify reset provenance, call the A34 evaluator, or
change lifecycle state.

## Exact wire contract

The audited format is little-endian and begins with sixteen 32-bit words. A
valid exact-Gemini prefix must satisfy all of the following without wrapped
arithmetic:

- at least 64 bytes are available for the header;
- signature equals `0x43474244`;
- the header's `sz_buffer` equals the supplied byte-buffer size;
- `off_pl` is exactly 64;
- `sz_pl` is at least four bytes and its 64-byte alignment is representable;
- `off_lpl == off_pl + ALIGN(sz_pl, 64)`;
- both current and previous preloader padded records fit;
- `off_lk == off_lpl + ALIGN(sz_pl, 64)`;
- `sz_lk` is exactly 64 for the pinned LK;
- `off_llk == off_lk + ALIGN(sz_lk, 64)`;
- both current and previous LK padded records fit;
- `off_linux == off_llk + ALIGN(sz_lk, 64)` and remains in bounds; and
- `off_console` is not before `off_linux` and is not past `sz_buffer`.

Only after those checks may the parser copy the little-endian 32-bit word at
`off_pl`. It must clear the caller's output on every error.

The parser deliberately rejects the downstream one-byte compatibility
fallback at fixed offset 12. It also rejects partially plausible headers,
including a correct signature with inconsistent chaining.

## Output contract

The typed output contains only:

- the complete raw current-preloader status word; and
- explicit validity.

Every bit pattern is data. The parser defines no normal, watchdog, cold,
external, safe, unsafe, or platform-epoch enum.

## Test contract

Focused KUnit must cover invalid arguments/output clearing, truncation, bad
signature, mismatched total size, corrupted preloader prefix, corrupted LK
suffix, exact-word round-trip, and every individual bit. Tests use allocated
ordinary memory only; no DT, reserved-memory, mapping, MMIO, reset, watchdog,
firmware, provider, or CPU operation is allowed.

## Deferred boundaries

The following require separate audits and patches:

1. locating and binding the exact `no-map` reservation;
2. copying it once without mutation and with defined writer ordering;
3. interpreting only values backed by a pinned preloader writer contract;
4. proving a fresh secure-platform epoch independently of reset-history
   fields; and
5. combining that authority with the pure A34 evaluator immediately before a
   fail-closed lifecycle publication.
