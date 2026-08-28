# Durable admission trace design

## Ownership

The existing mutable transition ledger retains exclusive ownership of dmesg
record 1:

- record 1: `0x44410000..0x44410fff`, physical transition ledger;
- record 2: `0x44411000..0x44411fff`, immutable controller entry;
- record 3: `0x44412000..0x44412fff`, immutable zero-request terminal.

All three records are inside the exact DT-reserved `0x44410000..0x444effff`
ramoops range. Record 2 and record 3 begin with the qualified logical-empty
header `DBGC`, start zero, size zero. This diagnostic never maps record 1.

## Exact records

Every payload begins at byte 12 and is one of these fixed byte strings:

```text
====0.000000-D
GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A kind=entry slot=2
```

```text
====0.000000-D
GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A kind=zero-source-register slot=3
```

```text
====0.000000-D
GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A kind=zero-derive slot=3
```

```text
====0.000000-D
GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A kind=zero-publish slot=3
```

The payload is committed byte-for-byte, followed by a full barrier, the
32-bit start length, a full barrier, the 32-bit size length, and a final full
barrier. The already-qualified `DBGC` signature is not rewritten. A complete
header and payload readback is mandatory. Any mismatch seals the boot-local
owner and permits no retry.

## Controller order

The controller core performs:

1. reject an already-consumed state without touching the trace;
2. commit or byte-exactly recognize the entry record;
3. test binder readiness and the late-ready token without consuming;
4. consume the one shot;
5. register the physical source;
6. derive the CPU8 transaction;
7. publish P17/P18;
8. increment the request count and call `add_cpu(8)` once;
9. unregister the source.

If steps 5, 6, or 7 fail, the core commits exactly one matching zero-request
terminal record after any required unregister and returns without incrementing
the request count. No record-3 write occurs on the request path; the binder and
transition ledger own all evidence after step 8.

## Decision map

| Record 2 | Record 3 | Transition ledger | Interpretation |
| --- | --- | --- | --- |
| empty | empty | empty | controller core not established |
| entry | empty | empty | core entered; prerequisite deferral or interruption before consumed terminal |
| entry | exact zero terminal | empty | exact consumed zero-request source failure |
| entry | empty | valid nonterminal/terminal | request reached the binder; classify its last physical stage |
| any foreign, torn, or conflicting combination | any | any | reject attribution and do not repeat |

USB/netcat remains a live positive path, but no decision branch depends on its
timing. Screen color and automatic reboot remain serviceability evidence only.
