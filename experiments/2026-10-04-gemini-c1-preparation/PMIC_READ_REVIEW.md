# C1 PMIC read semantics and updated ordering

Offline review, 2026-10-04. The [receipt](results/pmic-read-semantics.json)
pins the private document digest and exact target pages. No private document,
extracted text or render is published. No device operation was performed.

The roadmap review in `06769f76` supersedes this experiment's earlier Gemian
reset-policy prerequisite. C1 records `TOP_RST_MISC` after successful chip
identification and before IRQ initialization or child registration. The key
child then uses explicit one-key mode and an eleven-second duration, matching
the retained compiled policy intent. The planned action is one short key
press; physical long-press timing and recovery behavior remain untested.

| Target | Address | PDF pages | Field evidence |
| --- | --- | --- | --- |
| `TOP_RST_MISC` | `0x02b6` | 118, 119 | RW reset-enable/mode fields; source-defined timeout field omitted. |
| `STRUP_CON15` | `0x001e` | Not covered | not covered at this address; vendor header names power-off sequence controls. |
| `TOP_CKPDN_CON0` | `0x023a` | 96, 97 | RW clock-control word; SET/CLR aliases excluded. |
| `TOP_CKPDN_CON1` | `0x0240` | 98, 99 | RW clock-control word; SET/CLR aliases excluded. |
| `TOP_CKPDN_CON2` | `0x0246` | 100, 101 | RW clock-control word; SET/CLR aliases excluded. |
| `BUCK_VCORE_CON0` | `0x0600` | Not covered | not covered at this address; source defines enable/selector ownership controls. |
| `LDO_VDRAM_CON0` | `0x0a74` | 175, 176 | RW enable/mode controls and RO state; source-defined fields also omitted. |
| `CHR_CON1` | `0x0f7a` | 302, 303 | RW threshold fields. |
| `CHR_CON6` | `0x0f84` | 304, 305 | RW threshold/detection controls and RO detection state. |
| `CHR_CON13` | `0x0f92` | 306, 307 | RW watchdog controls; write effects do not establish read effects. |

The covered fields use ordinary RW/RO annotations rather than read-clear
annotations. This narrows the read-semantics uncertainty; it does not prove
undocumented bits or exact E2 applicability. The PDF leaves the reset timeout
field and several source-defined LDO fields blank. SET/CLR aliases, IRQ status,
RTC mailboxes and calibration registers remain outside the ten-word inventory.
Do not expand the subset from adjacent table entries.

The two uncovered words need a source-based read-effects review before device
use; their names and vendor initialization writes alone are insufficient.
Compilation of the key/lid settings can proceed independently. The observer
must retain address and transport result, omit values on failure, stop at the
first failure, and issue no PMIC write, retry or comparison-triggered update.
Its wrapper command/valid-clear effects remain those in the
[observation review](OBSERVATION_REVIEW.md).

Further RTC polishing does not gate C1 under the updated roadmap. Candidate
validation still needs the selected package identity and attended collection
boundary; no new candidate is admitted here.
