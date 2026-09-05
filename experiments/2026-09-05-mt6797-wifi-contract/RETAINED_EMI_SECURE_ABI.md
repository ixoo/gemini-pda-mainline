# Retained secure-firmware EMI set ABI

The retained TEE image contains a compatible EMI set dispatch and a concrete
region-18 implementation. The missing service is no longer merely a vendor
header declaration. Compatibility remains conditional on current firmware
identity, reservation ownership, address translation and region lock state;
this result admits no live provider or secure call.

## Identity and method

The existing private TEE image is 5,242,880 bytes, SHA-256
`2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
Its hash was verified before and after read-only analysis in the RE VM.
No image was captured, copied, extracted, modified or published. The existing
retained analysis mapping was reused: analysis address = file offset +
`0x000ff3c0`, payload file extent `[0x1000,0x17e00)`.

The [July 23 retained slot-identity observation](../2026-07-22-a72-firmware-power-contract/results/live-tee-identity-20260723.txt)
records both persistent TEE slots matching this image. It explicitly does not
claim a runtime secure-memory dump. That historical observation and this
retained-file hash do **not** prove today's active secure firmware identity,
its mutable lock bytes or which slot was executed. No new live verification
was attempted. The [earlier mapping audit](../2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt)
owns the retained mapping provenance.

Capstone 4.0.2 AArch64 decoding established the dispatch and handler paths;
GNU AArch64 objdump 2.42 independently checked ten instruction mnemonics at
the critical range, selector, region-18 lock/store and return sites. This was
a static control-flow interpretation, not firmware emulation or execution.
[Sanitized file-offset/address/window hashes](results/retained-emi-secure-abi.json)
permit reproduction against the exact privately held input without distributing
firmware bytes or disassembly. The public kernel call/header identities remain
in [the source ledger](results/whole-image-emi-sources.json).

## Executable dispatch and result paths

| Analysis address | Attributable behavior |
| --- | --- |
| `0x108588` | Constructs SMC32 `0x82000209`; equality branch at `0x108594` targets `0x109074`. |
| `0x108a50` | Constructs SMC64 `0xc2000209`; equality branch also targets `0x109074`. |
| `0x109074` | Passes saved x1/x2 as 64-bit start/end, low 32 bits of x3 as packed policy, and calls `0x105508`. |
| `0x10936c` | Zero-extends the returned w0 before the common saved-result store at `0x10945c`. |
| `0x105508` | EMI range normalization, policy/region selection and register writes. |

Thus the observed vendor SMC32 literal is implemented even though start/end
travel through 64-bit argument registers on this path. The SMC64 alias exists
in this retained image; that finding does not justify silently changing the
project's observed ABI or extrapolating it to another firmware revision.

The handler returns 0 after its programming sequence, -3 when the normalized
end unit precedes the start unit, -2 for a region outside 2 through 23, and
-4 when the selected protected region's software lock byte equals 1. The
invalid-range check precedes region validation. The generic unknown-service
path returns low-word `0xffffffff` (-1), but supported EMI-set dispatch does
not take that unsupported-service path. Region 18 and 19 both have lock checks.
These are executable return paths in the retained image, not observed device
responses. No per-domain policy validation or physical-reservation ownership
check appears in this traced handler.

A host adapter must interpret the low 32-bit return as signed. For example,
range failure arrives through the saved result as `0x00000000fffffffd`, whose
signed 64-bit interpretation would be positive. Casting the low word to signed
32-bit gives -3, consistent with the vendor kernel's `(int)x0`. This refines the
[lower-operation audit](WHOLE_IMAGE_EMI.md); the wrapper's lost result is still
a repairable defect. Success indicates the handler reached its store/return
path; there is no readback or independently observed hardware success here.

## Bit-level normalization is not input validation

Unless both start and end are zero, the handler reads `0x10001f00` bit 13.
If clear, it subtracts `0x40000000` from each 64-bit address; if set, it subtracts
zero. It then takes **bits 31:16** of each subtraction result. The resulting
16-bit start and end units are compared unsigned. Both-zero bypasses translation
and uses zero units; this audit does not infer a disable operation from that.

The handler does not reject unaligned inputs, an original reversed range within
one unit, addresses below the subtraction base or upper-address aliases. Low
16 bits are discarded; bits above 31 also do not survive extraction. In
particular this is not full-width address validation or an alignment check.
The public MT6797 header's `EMI_MPU_ALIGNMENT=0x10000` independently agrees
with the unit size. A caller requiring confinement must enforce an aligned
start and inclusive end ending in `0xffff`, and ensure its owner-provided
translation is representable without underflow, wrap or upper-bit aliasing.

For the synthetic interval `0x80000000..0x8007ffff`, the packed range word is
`0x40004007` with selector bit clear and `0x80008007` with it set. These are
arithmetic illustrations of the decoded path, not a live reservation or
register value. An unaligned final address can select an additional 64 KiB
unit, so accepting the old mock's byte-level bounds alone is insufficient for
a real owner. The active global selector must belong to an attributable owner
contract; this audit performs no live read of it.

## Region 18, neighboring 19, and policy authority

The handler takes permissions from bits 23:0, a software-lock request from bit
26 and the region from bits 31:27. Bits 24 and 25 are ignored in this routine.
Its 22-entry dispatch table maps region 18 to `0x105a90` and 19 to `0x105ae0`.

| Region | Lock byte (analysis address) | Packed range register | Permission register |
| --- | --- | --- | --- |
| 18 | `0x11dab0` | `0x10200370` | `0x102003b0` |
| 19 | `0x11dab1` | `0x10200378` | `0x102003b8` |

For each, lock == 1 returns -4 before writes. Otherwise bit 26 optionally sets
that byte to 1. The path issues `dsb sy`, clears its permission register,
issues another barrier, writes `(start_unit << 16) | end_unit`, issues another
barrier, then stores the low-24-bit policy through the common tail and returns
zero. The tail contains no final readback. The handler's lock latch is separate
from the vendor Linux spinlock; it is not a Linux resource lease. Its current
value, other firmware agents and concurrency guarantees are not established.

The public Linux wrapper first masks policy to 24 bits before packing the
region, so the audited WLAN/WMT requests cannot set lock bit 26 through that
wrapper. This does not prove the latch is unlocked at handoff. The inspected
region-18 path does not alter region 19's registers or lock byte; global memory
priority and other overlapping protection regions were not resolved.

The selected public WLAN source requests region 18 with all eight domain
fields set to 0, then policy `0xb6da2d` (domain field 2 is 0; the other seven
fields are 5). WMT requests region 19 with `0xb6da28` (fields 0 and 2 are 0;
others 5). The public macro packs three bits per domain and names 0
`NO_PROTECTION`, 5 `FORBIDDEN`. The retained handler writes these fields without
interpreting the domain names. Therefore the bit policies are source facts;
calling field 0 AP or field 2 CONSYS remains a master/domain-assignment inference
here. No DEVAPC assignment or active domain mapping was established by this
bounded EMI-handler trace. Neither policy words nor a successful return grant
ownership over the first half-MiB or the neighboring WMT extent.

## Concrete compatibility conclusion

The exact retained image supports the requested service, region 18, the public
packed policy representation and attributable error propagation. This removes
the absence-of-implementation uncertainty. A real provider must additionally
validate 64 KiB protection confinement, preserve the correct selector-dependent
translation and signed-low-word status, omit unapproved lock requests, hold the
reservation/remap lifetime, and treat lock denial or restoration failure as
terminal. It cannot claim current firmware, current lock state, AP/CONSYS domain
assignment or reserved-memory ownership from this static result.

No new model, live verification, kernel build, backend build, source push or
hardware action was added. The RE VM shell was closed after analysis; no new
VM files or analysis databases were created. The concrete remaining evidence
is current boot-chain identity and an admitted reservation/domain/translation
owner, rather than whether this retained firmware implements EMI set at all.
