# Retained kernel and secure-component SPM attribution

This bounded static audit follows source decision
`cf0d9f17b88423c432bc0ec32b845ef8a7d866bc`
([SPM key and order](SPM_KEY_ORDER.md)). It reuses one retained primary-boot
kernel and one retained TEE component in the RE VM. It does not read the device,
make a capture, build a kernel or execute any analyzed firmware.

## Decision-changing result

**The retained normal-world kernel itself enables shared SPM register control.**
Five named sites store key/enable `0x0b160001` at SPM `0x10006000 + 0x000`:
its SPM initializer, SPM helper, WMT ON preparation, and both CONN transitions.
The binary also confirms clock-disable before reset assertion during CONN OFF.
These findings close the source-to-retained-kernel attribution gap for those
operations. They do not show that a store executed during the current boot.

The selected secure component is a separate result: its five attributable
key-write constructions target **CSPM `0x11015000 + 0x000`**, not SPM. It also
contains a parameterized SPM bit-update helper, so an exact-address literal
search alone cannot establish absence of SPM writers. Its four reviewed direct
call sites address CPU/cluster controls rather than SPM `+0`.

No SPM `+0` writer or clearing operation was attributed in those selected
secure-component paths. This is a bounded negative result, not proof that
retained firmware never touches the register. Linux/firmware concurrency,
enable-state lifetime across suspend, and safe restoration remain unresolved.
No new provider flag, key-write implementation or active CONN candidate is added.

## Identity and mapping method

The kernel is the already-retained primary-boot capture associated with the
[July exact-boot audit](../2026-07-22-a72-firmware-power-contract/results/active-gemian-boot-binary-audit-20260726.txt),
not a filesystem package substituted for it. The existing reconstructed ELF
was reused. The private identity record verifies this chain:

1. Retained boot capture matches the earlier capture identity.
2. Its Android kernel field matches the earlier field identity.
3. Decompressing that field reproduces the retained `Image`; trailing data
   matches the retained board DTB.
4. The reconstructed ELF's `.kernel` section equals that `Image` byte for byte.

The TEE input matches the earlier retained component identity and uses the
[previously recorded extent and mapping](../2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt):
file offsets `[0x1000, 0x17e00)`, instruction address equal to file offset plus
`0xff3c0`. The selected component contains EL3 register accesses, consistent
with the earlier ATF attribution. No new symbolic names are invented for its
unnamed routines, and the map is not extrapolated to other payloads.

Binary hashes, reconstructed bytes, DT text, symbol listing and disassembly
remain in the private guest analysis directory
`~/reverse-engineering/work/wifi-spm-key-20260905/`. Its
`private-provenance.json` and `private-analysis.json` identify the exact inputs,
store sites and checks. No binary identities are reproduced in this addendum.
The immutable evidence and existing reconstructed kernel were not modified.

## Normal-world owners: high confidence in static attribution

| Named routine | Verified operation | Attribution basis |
| --- | --- | --- |
| `spm_module_init` | Writes key/enable to SPM `+0` during initialization | Maps `mediatek,sleep` resource 0; retained DT maps it to `0x10006000`; store uses that saved mapping |
| `spm_poweron_config_set` | Writes key/enable under its SPM lock | Uses the same saved mapping as the initializer |
| `mtk_wcn_consys_hw_reg_ctrl` | Writes key/enable after external reset assertion and before clock preparation | Uses the resource-3 mapping saved by `mtk_wcn_consys_hw_init`; retained CONSYS DT identifies that resource as `0x10006000` |
| `CONN_sys_enable_op` | Writes key/enable before power requests | Uses the mapping installed by `mt_scpsys_init` from DT resource 1, identified as `0x10006000` |
| `CONN_sys_disable_op` | Writes key/enable before protection and island shutdown | Uses that same mapping; contains no key save/restore on its return path |

The CONN enable routine requests primary then secondary power, waits for both
ACKs, clears clock-disable and isolation, releases domain reset, then releases
protection. The disable routine asserts protection, sets isolation, sets
clock-disable, asserts domain reset, clears primary then secondary requests,
and polls both ACKs OFF. Both use protection mask `0x60000`. These are binary
control-flow facts, not a successful transition receipt or safe rollback proof.

The separate normal-world mappings also rule out describing the vendor design
as a sole SPM owner with one common lock. Repeated same-value writes establish
what these routines do; they do not prove universal idempotence or authorize
clearing the shared enable when a CONN user detaches.

## Secure component: positive CSPM attribution and bounded SPM negative

Capstone and GNU AArch64 objdump independently decode the five key store sites.
Each constructs `0x0b160001` and stores it to `0x11015000`. The surrounding
paths use the separately addressed secure CSPM semaphore. This corroborates
the earlier CSPM-owner result; the identical key value is not SPM attribution.

Three address constructions also form `0x10006000` in two small helpers: a
bit reader and a bit read-modify-write helper. Their effective target is that
base plus the caller's offset argument. Both store branches in the update
helper were checked with both disassemblers. Four direct calls to it were
traced back to offset construction:

| Caller family | Offset passed | Reviewed argument bound |
| --- | --- | --- |
| Two cluster sequencing loops | `0x210 + 4 * cluster` | Located direct and tail entry calls pass 0 or 1 |
| Two CPU sequencing loops | `0x220 + 4 * cpu` | Local unsigned admission requires CPU index at most 7 |

These direct paths therefore address SPM `+0x210/+0x214` or
`+0x220..+0x23c`, not `+0`. The helper itself is parameterized and is not a
hardware-enforced address restriction. Indirect entry calls, computed aliases,
other components and other constant-construction forms remain unexcluded.
There is no claim of exhaustive firmware coverage or of no SPM access.

A preliminary mnemonic query missed Capstone's `movz` spelling. The corrected
query reviewed all nine low-half `0x6000` constructions: three form the SPM
helper base, five form another peripheral address, and one forms a data value.
The preliminary zero was discarded. No exact little-endian SPM base/key literal
was found in the selected extent, but that negative is not used to exclude the
parameterized helpers discovered by instruction analysis.

## Consequence for implementation

A future SPM-owned implementation no longer needs to assume that the selected
vendor kernel relied exclusively on LK to enable register control: it demonstrably
contains its own enabling writes. The supported CONN OFF order is also tied to
the retained binary, rather than only to related public source trees.

What remains missing is narrower: attribution of any retained-firmware SPM
`+0` writer/clearer outside these paths and evidence for when enable state can
be lost or safely changed. The selected TEE paths do not establish a shared
lock, a suspend lifetime guarantee, or a restoration contract. This audit stops
at that boundary; it does not turn a bounded negative into authorization for a
new global write or extend the work into firmware reimplementation.

## Publication boundary

This document contains independently written register, call-role and control-flow
analysis. It includes no firmware bytes, instruction listing, decompiled/vendor
code, calibration, identifiers or proprietary document excerpts. Raw inputs and
analysis products remain private; no redistribution right for the underlying
firmware is claimed. Static attribution has high confidence where the mapping
and store are traced; exclusion of other owners and current runtime behavior
remain unproved. Validation is recorded in the
[receipt](results/retained-spm-attribution-validation.txt).
