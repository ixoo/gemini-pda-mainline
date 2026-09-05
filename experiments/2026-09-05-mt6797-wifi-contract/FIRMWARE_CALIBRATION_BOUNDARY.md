# Retained firmware calibration investigation boundary

The bounded retained-firmware inspection does **not** establish whether on-chip
EFUSE, compiled defaults or the submitted WIFI record takes precedence. It does
establish that encryption is not a blanket obstacle to offline investigation:
the retained MTKE image has two plaintext EMI sections, and calibration-source
terminology occurs in the latter. No command handler or precedence branch has
yet been attributed. The record remains a viable local input candidate under
the conclusions in [CALIBRATION_APPLICABILITY.md](CALIBRATION_APPLICABILITY.md).

## Inspection and negative result

The immutable retained firmware was read into memory in the existing RE VM;
its identity is the previously recorded [MTKE receipt](results/firmware-mtke.json).
No new hash, export, extraction, analysis database or firmware copy was made.
The input extent and four-section bounds were checked against that receipt.
Sections 0 and 1 are marked encrypted; sections 2 and 3 are not. The latter
contain 331296 and 65392 bytes respectively. None of the four section starts
has ELF magic; this does not identify their instruction set or code/data role.

A case-insensitive byte scan for `nvram`, `efuse`, `eeprom` and `calibration`
found no matches in section 2. Section 3 contains ten distinct bounded
NUL-delimited spans containing the first three terms; no `calibration` match
was found. A span starts after the preceding NUL and ends at the next NUL,
and is accepted only when at most 512 bytes long. These are search anchors,
not decoded functions, assertions that the spans are all printable strings,
or evidence of executed behavior. No private span text or values are published.

For each accepted span, the scan formed a candidate absolute address from the
section's container destination plus the span offset, modulo 2^32. It counted
the corresponding four-byte little- and big-endian representations throughout
both plaintext sections. Both counts were zero. This narrowly rules out that
literal-pointer search as a route to those anchors under that address model.
It does not rule out split immediates, relocations, a different firmware-visible
mapping, pointers into a span, references from encrypted code, or unused text.
It is not a recovered command-dispatch or data-flow result.

## Feasibility and pairing limits

The pinned comparative investigation identifies the code family as NDS32 and
reports unsuccessful MT6797 decryption using a different MT7697 device. That
is useful architecture guidance, not exact retained-image attribution or proof
that decryption is impossible. Its discussion of EFUSE key banks concerns
decryption keys, not RF calibration precedence.
[Pinned comparative notes](https://github.com/cyrozap/mediatek-wifi-re/blob/bcbb3b914ce1292add14bffdee4f1e0a8af33500/Notes.md).

The installed Ghidra 12.1.2 includes NDS32 definitions for both data byte
orders, with big-endian instructions in both definitions. The installed native
objdump is ARM/AArch64-oriented; the examined Radare2 plugin listing did not
provide an NDS32 decoder. There is therefore an available offline decoder;
tool absence is not the blocker. No speculative ARM or newer-chip Xtensa
disassembly was used. This slice did not run Ghidra analysis or establish a
firmware-visible mapping, executable entry points, ABI or reachable handler.
Those are the precise missing premises for a defensible firmware-side trace;
keyword counts cannot replace them. Plaintext sections may support such a trace
without decrypting the first two sections, but that feasibility is not yet a
demonstrated result.

The selected public gen3 source proves the host record layout, version check,
normal command framing and the unconditional final `0x48` submission after
optional overrides. It does not bind the retained file's internal handler to
that source revision. Co-retention, a matching filename/container, the host
record-version predicate and equality to producer defaults outside MAC do not
prove that firmware interpretation. No applicable capability response or
runtime record-application observation was recovered in this slice.

For the real loader, preserve the exact local 512-byte payload and its private
board/source context. Do not substitute defaults, infer an EFUSE selector from
omitted optional commands, synthesize an application ACK, or convert this
inconclusive static result into a new requirement for non-default RF bytes.
[NORMAL_COMMAND.md](NORMAL_COMMAND.md) owns the completed host transaction
helper and its submission-versus-observation boundary. This investigation adds
no radio action budget, device operation or global hardware-admission gate.
Ordered work remains owned by [the roadmap](../../docs/ROADMAP.md).

Validation was read-only retained-file inspection and source/tool capability
review. No calibration precedence, decoded handler, firmware/record pairing,
kernel behavior or hardware support is claimed. Host and VM storage were
checked; no temporary VM state was created and the RE shell was closed.
