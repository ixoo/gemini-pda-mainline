# Symbol provenance: parser invocation scope conflict

All frozen identities match. Pinned source inspection explains the synthetic
zero sizes and section mapping, and shows that ELF binding derives from
Kallsyms type/case rather than being uniformly invented as GLOBAL. See the
field transformations and exact citations in [analysis.json](analysis.json).

The parser recovered four unique original `T` tuples matching the predecessor's
ELF addresses, with no aliases and monotonically ordered neighbors. Their
provisional envelopes span 368, 280, 760 and 160 bytes respectively; full bounded
metadata is in [intervals.json](intervals.json). Original `T`, rather than
reconstructed GLOBAL alone, supports an ordinary global-text classification.
No envelope is promoted to an exact function end.

Acceptance is withheld. `KallsymsFinder(Image, bit_size=64)` unconditionally
invokes architecture detection. Its admitted source identifies ISA-prologue
signature detection, conflicting with the contract's strict prohibition on
instruction-byte classification. No disassembly or instruction bytes were
output, but the no-classification condition cannot truthfully be claimed.
Inspection stopped immediately after confirming that internal call path.

The next discriminator is an explicitly admitted architecture-bypass parser
invocation using the frozen AArch64/little-endian identity. Do not start later
instruction analysis from these provisional envelopes. Raw parser output and
bounded metadata remain private in the RE VM; only hashes and bounded symbol
facts are published here. No new ELF, network lookup, device action, build,
commit or push occurred.

The [freeze](FREEZE.md) and [validation record](VALIDATION.md) cover this
escalation packet. Tests verify preservation of the unresolved boundary; they
do not retroactively admit the parser invocation.
