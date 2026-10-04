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


The [retained patch-order analysis](ROM_PATCH_ORDER.md) now identifies the
source/loader metadata order and address bytes for the exact private pair.
Sequence 1 is filename suffix `1_1`, then sequence 2 is `1_0`; lexical order
would be wrong. Its fragment arithmetic matches the retained Gemian summaries.
Installed attribution, hardware/ROM-version applicability, full-STP transport
and powered failure handling remain separate before a candidate.

The [full-STP framing follow-up](FULL_STP.md) now supplies a hardware-free WMT
codec and corruption/boundary fixtures. ACK state, reset epochs, FIFO progress
and hardware acceptance remain unresolved; the codec does not admit transfer.

## PA source/config follow-up

The [PA source join](results/pa-source-join.json) pins the selected Gemian
platform implementation and header to the same prepared source and v8
configuration. The header selects separate BT and Wi-Fi VCN33 controls, with
PMIC control enabled; the configuration contains no legacy PMIC option. In
that source branch each enable requests 3.3 V through its regulator handle
and calls regulator_enable. Voltage-setting failures are ignored, enable
failures are only logged, and the wrapper returns zero. Each disable also
ignores its regulator result. These policies cannot establish checked rail
transitions and must not be copied into the future executor.

The current mainline driver describes distinct BT/Wi-Fi enable registers but
a shared voltage-selector register and mask. This is a driver-description
fact, not new hardware validation. The future owner needs both standard
regulator handles, shared-selector accounting and per-operation failure
records. The unselected shared software counter and legacy PMIC-control
writes are not substitutes. This review performs no rail or calibration
action and supplies no live calibration-event or voltage-transition proof.

## Connectivity AFE power-on stage

The [AFE source join](results/afe-source-join.json) independently checks the
same selected platform source and header hashes as the PA review and extracts
eleven active, ordered writes within `0x180b6000 + 0x100`. This resolves the
revision difference between the [GNSS finding](../2026-10-04-gemini-gps-re/README.md)
and the current Wi-Fi reference: the stage exists in `59e00a91` too. It runs
after the chip-ID poll and MCU ACR update, before MCU reset release. A future
CONSYS implementation must place it there rather than append it to GNSS-on
or to a running WMT session.

The selected source does not write WF_TX_02 at offset `0x8c`; that operation
is commented out. GPS_SINGLE at `0x14` is conditional on
`CONFIG_MTK_GPS_REGISTER_SETTING` and is outside the eleven-write list. Do
not enable it from a header constant alone. The vendor's 64-word debug read
loop and unchecked `ioremap_nocache` failure handling are not requirements
to reproduce. Claim and map the analog resource before any power-on writes,
reject missing or conflicting ownership, and preserve the existing reset and
powered failure contracts. Do not assume readback proves undocumented analog
effects or add broad register dumps to production initialization.

The receipt records independent register facts, not copied source. Hash
verification, extraction count and aligned offsets within the mapped window
passed offline. Register meanings, safe readback behavior and the effect on
Wi-Fi reception remain unproved; no hardware operation or build occurred.

The [AFE driver preparation](../2026-10-04-mt6797-afe-preparation/README.md)
implements this sequence behind an explicitly claimed optional resource;
compile/schema validation and hardware admission remain separate gates.

## Shared task framing preparation

The [task framing checkpoint](../2026-10-04-mt6797-stp-task-framing/README.md)
extracts the ordinary task codec for Bluetooth while preserving the existing
WMT API and command ceiling. Host and Buildbox checks pass. Shared task delivery,
sequence/ACK ownership, IRQ lifetime and reset epochs remain separate transport
work; this checkpoint supplies no Bluetooth or GNSS hardware result.

The [shared link-state checkpoint](../2026-10-04-mt6797-stp-link-state/README.md)
now prepares the seven-frame cumulative ACK window and shared receive sequence,
and moves the existing WMT client onto it. Host and Buildbox checks pass;
production Bluetooth/GPS delivery, retransmission and client/reset lifetime
remain unwired and untested on hardware.
