# Common initialization: selected branches and failure policy

This offline follow-up narrows the next common-initialization candidate after
[first-query transport liveness](../2026-10-03-mt6797-wmt-default-query/README.md).
It changes no installed image, effect budget or hardware admission.
The [source/config receipt](results/common-init-review.json) joins the retained
v8 configuration to its prepared Gemian source and inherited Makefiles.
The WMT startup source, script helper and STP header are byte-identical to the
previously reviewed private copies. This is a source/config join, not an exact
compiled-function equivalence or live calibration result.

## Selected branches

| Branch | Evidence and selected behavior | Candidate implication |
| --- | --- | --- |
| LTE filtering | v8 `CONFIG_MTK_CONN_LTE_IDC_SUPPORT=y`; connectivity Makefile defines `WMT_IDC_SUPPORT=1` and the abstract STP interface; STP header enables LTE handling; SoC source enables filter settings | Review the 0x0279-selected LTE/coexistence commands and applied configuration before full initialization |
| VCN33 efuse voltage adjustment | Common Makefile defines the efuse branch only for MT6580; selected board is MT6797 | Do not add this unselected voltage-setting operation to reproduce the reference path |
| Merged PCM | Common Makefile selects merge support only for MT6628/MT6630/MT6632; selected chip is CONSYS_6797; platform header selects zero | Omit the unselected merged-interface command |
| DLM | SoC source enables the DLM table | Three ordered masked firmware register operations require their own effect review; they are not an optional skipped step |
| MCU clock | Chip 0x0279 selects its own enable and restore tables around all patches | Keep the selected order, verify every event, and define failed-step lifetime before hardware admission |
| Trim and co-clock | Selected source disables trim; retained Gemian log reports co-clock disabled | No trim or oscillator-setting operation follows from these source paths |

The earlier LTE build-branch uncertainty is narrowed by this source/config join.
Exact preprocessed/binary confirmation and applied LTE fields are not claimed.
No unrelated PMIC conversion or efuse experiment is a prerequisite for PIO.

## Failure behavior must be explicit

The vendor script helper verifies sent length and received length. For a
received event whose second byte is opcode `0x14`, it skips complete expected
content comparison. Consequently, reaching coexistence supports completion of
the vendor calibration script under this source path, but does not prove that
its calibration event carried a checked success status. Preserve the original
retained observation and its inference; do not turn it into a stronger claim.
A future mainline calibration validator needs reviewed opcode, length, status
and result semantics, attributable private event capture and an explicit pass
predicate. Firmware's ordinary command responsiveness is insufficient.

DLM and MCU clock script errors are logged and then overwritten by subsequent
work. PA control similarly overwrites the BT enable result with the Wi-Fi enable
result. Calibration failure returns before the paired PA-off requests. These are
observed source policies, not a mainline error-handling template. The future
owner must record each completed step, stop at the first failure and preserve
the admitted powered lifetime until reviewed recovery. Do not blindly send
cleanup writes after an unknown command outcome or proceed to WLAN START.

The enabled DLM script sends three ordered masked register operations to
`0x80100060`, all with value zero, with masks `0x00000f00`, `0x000000f0` and
`0x00000008`. This decodes the source's wire fields only. The bit meanings,
write effects and reset applicability still need a matching register/firmware
contract; no such write is admitted by this document.

## Patch transfer requirements

The selected multi-patch source strips a 28-byte header and sends the body in
fragments of at most 1000 bytes. Each patch first requires two checked address
command/event exchanges. Each body fragment has a first/middle/last flag and
requires its exact five-byte event before advancing. A one-fragment body uses
the last flag. Reset follows each completed patch; MCU clock restoration follows
all patches. Do not reuse the current fixed 16-byte query parser for these
variable-length full-STP transactions.

Before a candidate, pin the private patch order, lengths, headers, addresses and
hashes to the actual loader selection; enforce integer and fragment bounds;
review full-STP sequence, acknowledgement, checksum and flow-control behavior;
and reject partial, malformed, duplicate or unexpected events without an
unbounded retry. Distinguish a script event from effective firmware state.
Complete the selected LTE, PA/calibration, coexistence and FM-strap contracts
before composing common initialization with the existing WLAN START/scan path.
These are preparation requirements for the existing roadmap step, not new
physical tests or permission to bypass first-query liveness.
