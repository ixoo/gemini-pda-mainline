# Pure C EMI argument and result helper

[`src/emi_abi.h`](src/emi_abi.h) is an original, standalone arithmetic helper
for a future real provider. It issues no SMC, maps no memory, reads no selector,
changes no resource and returns no lease. It neither copies retained firmware
code nor changes the seven frozen protocol headers. The kernel-integration
worker confirmed no interface conflict and will keep it separate from transport
and provider admission.

## Interface and provenance

`mt6797_emi_prepare(owner, start, end, permissions, arguments)` accepts an
explicit `mt6797_emi_owner_range`: inclusive reserved bounds, an explicit
selector enum and the region owned by the caller. The caller must already hold
that ownership and a stable selector context. This plain struct is not proof
of ownership, an acquisition operation or a firmware compatibility decision.
Selector zero/unknown is refused, preventing accidental default selection.
Output must be distinct from input storage and is cleared on every refusal.

Success returns prepared function ID, original 64-bit start/inclusive end,
packed region/policy and an expected range word for inspection. The range word
is not written by the helper. Local invalid context/policy returns `-EINVAL`;
invalid interval/confinement/representation returns `-ERANGE`. These local
errors are distinct from interpreting a firmware result.

| Rule | Normative basis |
| --- | --- |
| Fixed observed SMC32 function ID; original 64-bit range arguments | Retained dispatch at `0x108588`, call at `0x109074`; public wrapper/header in the lower-operation audit. |
| Explicit selector translation: subtract `0x40000000` when bit 13 is clear, zero when set | Retained handler `0x105510..0x105538`. The helper receives context; it does not read the register. |
| Region 2 through 23; low 24 policy bits | Retained selection at `0x105554..0x105584`. Accepted region numbers still require owner authorization. |
| Reject bit 26 and all high policy bits | Deliberate caller restriction: bit 26 latches protection in the retained region paths; the public wrapper strips high bits. The helper refuses rather than masks. |
| Require start aligned to 64 KiB and end ending `0xffff` | Caller confinement restriction, because the retained handler extracts bits 31:16 instead of rejecting unaligned inputs; public header alignment agrees. |
| Reject original reversed ranges, including within one unit | Caller restriction beyond the retained normalized-unit comparison at `0x10553c`. |
| Reject underflow, upper-bit aliases and out-of-reservation spans | Caller restriction before the retained subtraction/extraction can erase information. |
| Decode signed low word, preserve full raw result | Retained result tail `0x10936c` zero-extends w0; public kernel casts the result to int. |

The exact decoded paths, file offsets, hashes and separation from current
runtime state are owned by [the retained ABI audit](RETAINED_EMI_SECURE_ABI.md).
Public declarations and the dropped-result defect are owned by
[the lower-operation audit](WHOLE_IMAGE_EMI.md).

The entire owner reservation must fit the selector's representable interval:
`[0x40000000,0x13fffffff]` when clear or `[0,0xffffffff]` when set. Checks precede
subtraction and avoid computing an overflowing exclusive end. The requested
aligned protection interval must lie within that reservation. Original
addresses above 4 GiB can therefore be arithmetically representable in the
clear-selector case after subtraction; they are not silently truncated.
This reflects the retained 64-bit argument path and does not prove that any
such address is physically owned, reachable or permitted on the device.

`mt6797_emi_decode_result(raw)` returns a struct containing `raw` and signed
low-word `status`, with defined C arithmetic even at INT_MIN. It does not map
firmware codes to Linux errno or collapse unknown values. Known -1/-2/-3/-4,
unknown negative/positive values and all high bits are preserved appropriately.
The caller examines status; a zero status is not ownership or hardware-support
admission. A nonzero high word is retained for diagnosis, without inventing
an additional firmware-success rule.

## Validation and integration boundary

[`src/emi_abi_test.c`](src/emi_abi_test.c) checks both literal sample range words,
region/policy packing, every nonzero low-16-bit start offset and every end value
other than `0xffff` (131,070 alignment refusals), reversed and external ranges,
unknown/default selectors, missing owner/output, each high policy bit including
lock, all region values 0..31 plus UINT_MAX, full representability edges and
underflow/upper-alias/maximum-integer cases. Refusals must clear every output
field. Fifteen explicit raw/status cases include all declared statuses,
unknown values, signed boundaries and nonzero high words.

Strict C11 with `-Wall -Wextra -Werror -pedantic -fsanitize=address,undefined`
passes on the host. [Validation receipt](results/emi-abi-validation.txt).
Build the linked C test with those flags and run its executable inside a managed
temporary directory with an immediate cleanup trap. No kernel build or backend
was run; the `__KERNEL__` include branch is not compile-verified by this result.

This helper prepares an operation only. A real provider must still establish
current firmware compatibility, reservation and region lifetime, domain policy,
selector stability, shared-resource serialization, copy visibility, failure
recovery and safe release. It must preserve this separation when connecting the
helper to an actual call. No global success flag, caller-set completion lease,
firmware readback substitute or live operation is introduced.

## Coordinator integration review

The coordinator reviewed the arithmetic, signed-result conversion, refusal
fixtures and supporting sanitized ABI record. Independent strict C11 execution
with warnings-as-errors, conversion warnings, AddressSanitizer and
UndefinedBehaviorSanitizer passed the 131,070 alignment refusals and the
selector/range/policy/result cases. Temporary executable state was cleaned.
The retained-firmware disassembly was not independently repeated; its exact
input identity, method and current-state limits remain in the owning audit.
This accepts the pure helper for further implementation, not a live secure
call or kernel-compiled provider. The separate ownership proposal's referenced
upstream reserved-memory and mapping APIs were checked at its pinned revision.
