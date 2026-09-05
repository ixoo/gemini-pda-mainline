# Synthetic whole-image planner and EMI owner boundary

This implements the bounded follow-up to [the lower-operation audit](WHOLE_IMAGE_EMI.md)
(local audit commit `4a72f1ea`). It provides an original host-side sequencing
model and tests, not a live EMI provider, kernel loader or hardware admission.
No firmware file is opened. The seven frozen C protocol headers are unchanged.

## Implemented contract

[`wifi_whole_image.py`](scripts/wifi_whole_image.py) accepts bounded bytes or
a bytearray, takes an immutable snapshot, then reuses `parse_mtke` for CRC,
source/table bounds, destination overflow, overlaps and EMI-window checks.
Inconclusive formats/reserved semantics are refused. It extracts a tuple of
frozen sections containing immutable bytes for private in-memory execution.
These addresses, key selectors and bytes are never printed or serialized by
the module; it has no command-line entry point or file-reading function.
Ordinary encryption flags and masked key selectors are forwarded to the
ordinary transport; EMI bytes are copied unchanged, without host decryption.

The caller supplies actual `EmiOwner` and `OrdinaryTransport` implementations.
Acquisition returns an `EmiLease` bound to one `Session`, a checked immutable
`Reservation` and explicit immutable `Protection` policies. Booleans, absent
objects and leases for another session are refused. The provider is responsible
for an exclusive reservation, lifetime, mapping, remap exclusion, domain policy
and ownership checks; this Python abstraction does not establish those facts
on hardware. These are trusted provider objects, not protection against hostile
Python code mutating private state. No production provider is supplied.

Reservation validation uses subtraction bounds. The first 512 KiB must fit;
base/size must fit the conservative nonzero 32-bit synthetic address envelope.
Each EMI offset/length must fit that window, independently of a larger adjacent
reservation. The provider receives offsets for copies, never unchecked caller
physical addresses. This deliberately refuses wider addresses pending the
firmware ABI investigation; it does not infer alignment/granularity or physical
reachability. The mock allocates RAM and proves the adjacent half-MiB unchanged.

The secure boundary receives the observed literal **SMC32 `0x82000209`**, even
for the audited ARM64 call path, an inclusive first-window range and region 18
packed with explicit 24-bit provider policies. No default permission policy is
chosen. The mock policies 0 and 1 are test values, not an asserted hardware
AP/CONSYS policy. The boundary requires a signed 32-bit integer: zero is success;
-1 through -4 and unknown nonzero values raise `SecureFailure` preserving the
original signed status. Booleans, unsigned encodings of negative status and
other malformed representations are refused. A future actual adapter must
convert its ABI return register correctly; this module performs no SMC.

## Sequencing and failure behavior

One `step()` submits one section, in table order. Indices 0 and 1 go through
`OrdinaryTransport.submit`, whose contract is successful CONFIG ACK plus all
PDA submissions for that section. The synthetic tests use a recorder here;
they do not claim to execute the frozen C transport or establish a real ACK.
A future bridge must invoke that existing implementation, preserving separate
TC4 CONFIG and TC0 START credits and the common sequence history.

Later entries go through the held EMI owner. The model opens the writable
policy once for the EMI batch and copies each validated section. This is an
explicit composition choice, not a claim that the vendor per-entry protection
sequence was identical. Provider ownership must span the entire batch. After
all sections, a separate step establishes copy visibility, requests the final
restricted policy and checks ownership before entering `READY`. No section
completion, parser result or provider Boolean can directly authorize START.
`start()` only accepts `READY`; its successful result is `START_SUBMITTED`,
not firmware readiness or usable Wi-Fi. Ownership is checked around actions.
The reentrancy guard prevents callbacks recursively advancing the image.

Any operation failure makes the image terminally `FAILED`. If writable
protection was attempted, one bounded restriction attempt is made under the
same owner unless final restriction was already attempted. This accounts for
side effects before an error. The first error and any recovery error are kept
separately; a failing final restriction is already the first error and is not
retried. Lost ownership prevents that recovery call. There is no retry,
credit refund, reset or automatic START. `abort()` supports external deadlines
or cancellation, with the same terminal behavior and bounded recovery.

**The planner never releases a lease, including after successful START.**
Firmware may continue consuming EMI memory. The surrounding provider must
retain it for the firmware lifetime and own safe shutdown/recovery. This
module intentionally has no recovery/release implementation and no runtime
caller. Finite section steps do not impose a timeout on an individual provider
callback; the real owner/transport must provide its admitted bounded behavior.

## Validation and remaining integration boundary

[`test_wifi_whole_image.py`](scripts/test_wifi_whole_image.py) uses synthetic
MTKE bytes and a RAM-backed owner. It checks literal secure-call arguments,
ordered ordinary/EMI actions, adjacent-memory preservation, each declared and
representative unknown status at opening and final restriction, malformed
status representations, both copy failures, visibility/restoration failures,
retained primary and secondary errors, every ownership-check failure,
reservation/range edges, input snapshot immutability, owner/session binding,
double acquisition, invalid images, reentrancy, cancellation and premature or
repeated START. Images with 1, 2, 3, 4 and 8 sections exercise complete accounting.
The existing parser suite independently exercises its structural refusals.

Run both host suites with `python3 -B` on their linked paths.
[Validation receipt](results/whole-image-planner-validation.txt).
Hardware admission still requires the deployed secure ABI, alignment,
domain identities and actual reserved-memory ownership described in the audit.
A kernel provider and a bridge to the existing C ordinary/START implementation
remain unimplemented; there is no build/backend or device action in this change.

## Coordinator review

The coordinator reviewed the complete planner and synthetic tests at `c90af584`
and independently reran all 20 planner tests successfully. The literal secure
arguments and expected action order are checked against explicit test values;
failed copy and protection operations retain failure and prohibit another START.
The reservation remains retained after successful START for firmware lifetime.
The ordinary transport is still a mock: these results do not prove that the
actual C protocol is invoked. Connecting that implementation is separate work.
No hardware access or firmware input was used in this review.
