# Experiment: supplied documentation collection assessment

## Record and method

Status: completed

- ID: `2026-09-29-documentation-collection-review`
- Scope: offline usefulness assessment; documentary claims remain unvalidated
  on silicon unless linked to existing project evidence.
- Device: named MT6797X Gemini; no device accessed.
- Baseline: `fbbc851b159b1553c93a6e38d859f8e26b0bbc52` plus the earlier
  uncommitted functional-specification and MT6351 review notes.
- Investigator: Codex, at owner request; no tracking issue created.

Reviewed the owner's 19-file collection: README, manifest and 17 sources.
All 17 source SHA-256 digests and byte sizes matched the supplied manifest.
[`sources.json`](sources.json) records filenames, URLs and exact identities;
URLs describe supplied provenance, not independent download authentication.
The local reference copy is under ignored
`artifacts/reference-docs/Gemini-PDA-Mainlining-Docs/`, retaining all 19 original
filenames including README and manifest. Every copied file matched its source
SHA-256 and size; the 17 manifest entries also verified. Source originals were
preserved. The collection directory is mode 0700 and files are mode 0600;
all copies were verified ignored and absent from the Git index. This local
retention does not grant redistribution rights.
Reviewed source types and contents, then examined chapters relevant to current
unknowns against existing project records. This is not a line-by-line audit of
3,097 register-table pages or an electrical validation of every component.
Poppler extracted searchable text; selected decisive tables and diagrams were
also rendered and visually checked. Page references are one-based PDF pages.

No third-party documents, extracted text, screenshots, code or private evidence
are copied into this repository. No kernel build, device read, boot, firmware
execution, rail operation or support promotion occurred. Reproduce by checking
the identities and cited pages against the linked project records.

## Reconciliation with main (2026-10-17)

Restored against `598040b5`. The table and findings below describe the September
review. Newer records own the implementation and device chronology:

- [Charger REG06 access review](../2026-10-04-gemian-session-a/REG06_ACCESS_REVIEW.md)
  already covers REG0C fault-history consumption. The
  [C2b charger record](../2026-10-06-gemini-c2b-charger/README.md) owns verified
  charge-start work; the earlier general caution is not a replacement protocol.
- [Display RE](../2026-10-04-gemini-display-re/README.md) and
  [display H2/H8](../2026-10-06-gemini-display-h2/README.md) supersede the old
  display-clock discovery plan. SSD2092's documentary TDDI classification,
  unidentified-bias EEPROM boundary and PWM update fields remain useful
  constraints without proving this unit's controller identity.
- [PMIC basics](../2026-10-04-gemini-pmic-basics-re/README.md) and
  [microSD power work](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md)
  already cover control ownership and trim preservation. The
  [buck-conversion conflict](../2026-09-28-mt6351-datasheet-review/README.md#highest-priority-finding-buck-voltage-conversion-conflict)
  remains unresolved. AUXADC/AW9523/FUSB301A read effects and source-table
  defects below remain reference constraints, not new observer protocols.
- [Bounded Wi-Fi runtime](../2026-10-07-mt6797-wifi-phase-b-join/RUNTIME_31_RESULT.md)
  supersedes the earlier first-execution EMI blocker. Historical omission of
  an overlap/routing contract from these documents does not negate later work.

The [roadmap](../../docs/ROADMAP.md) retains current ordering. Original source
hash checks and validation below describe the original review, not a new
revalidation of retained documents during restoration.

## Source-by-source disposition

| Supplied source | Assessment and useful boundary |
| --- | --- |
| MT6797 functional specification, 291 pages | High architectural value, known erroneous examples. Extracted text is byte-identical to the previously supplied `MT6797.pdf`, despite different PDF digests. Reuse the [existing assessment](../2026-09-28-mt6797-functional-spec-review/README.md); these are not two independent corroborations. |
| MT6797 register table part 1, 1,637 pages | High value for exact masks, access effects and offset comparisons. Focus: EMI pp.256-343, HIF DMA pp.418-419, AUXADC p.1084 and Wi-Fi HIF chapter beginning p.1397. Does not close effective EMI routing or overlap arbitration. |
| MT6797 register table part 2, 1,460 pages | High future value for display components; PWM pp.703-706 identifies shadow commit and update-source controls. A register description alone supplies neither Gemini wiring nor an initialization sequence. |
| 96Boards documentation index | Discovery/provenance aid for the above; not independent silicon evidence. |
| X20 schematic, 21 pages | Same digest as the already reviewed development-board schematic. Reference architecture only: p.1 explicitly has DA9214, MT6631, MT6351 and a USB-hub/DC-input topology unlike Gemini. Never transfer its net ownership or rail values to Gemini. |
| X20 BOM, 4 pages | P.3 independently locates part numbers within this board's BOM: U2201 DA9214, U5003 MT6631 and U2001 MT6351. It accompanies the same board design, not independent confirmation of Gemini assembly. |
| Gemian HardwareHacking | Useful discovery leads and explicit sensor-variant warning. Adapter/client names include inactive candidates; the page mixes Gemini, Cosmo and Astro. Its RT9466/RT5735 labels do not override named-unit identity evidence. |
| DA9213/14/15 datasheet, 62 pages, Rev.03.61 | Strong matching-family reference for the [observed legacy interface](../../docs/hardware/da921x-i2c6-a72.md). Pp.26-27, 32, 46 and voltage tables pp.51-53 help qualify production ownership. Does not uniquely identify which family member is fitted. |
| MT6351 MFD/header submission, 2017 | Historical proposal containing offsets and IRQ names, useful for source lineage and cross-checking. Submission is not upstream acceptance, revision-specific correctness or a new independent electrical authority. |
| MT6351 binding proposal, 2017 | Historical names/examples, not today's binding contract. Its VS1/VS2/VPA examples all use 600000-1393750 microvolt constraints, repeating the voltage-family concern in the [MT6351 assessment](../2026-09-28-mt6351-datasheet-review/README.md). A ramp-delay value is not a voltage-selector step. The actual regulator-driver patch is linked but not included in this collection. |
| AW9523B English datasheet, 21 pages, May 2016 V1.1.1 | Useful GPIO electrical/reset/IRQ contract, especially pp.10-11. Adafruit-hosted manufacturer document; not the newest version listed by the supplied manufacturer index. |
| AWINIC manufacturer index | Lists DS_AW9523B_EN_V2.4 plus hardware/software design guides. Those documents are absent; their contents and any errata were not reviewed. Worth retrieving when preparing IRQ work. |
| FUSB301A datasheet, 15 pages, Rev.1.6 | Useful CC/status/interrupt contract, pp.3, 9-10. Supplied provenance says official download failed and distributor mirror was used. Register identity agrees with retained probe values, but does not map physical ports. |
| BQ25896 datasheet, 65 pages, SLUSC76C | High value for charger ownership, fault-read effects and watchdog transitions, pp.25, 31, 41. Matching silicon is already recorded; battery settings and board power routing remain separate. |
| TPS65132 datasheet, 68 pages, SLVSBM1H | Valuable protocol comparison for unidentified bias hardware. Pp.16-19, 24 distinguish volatile registers, persistent EEPROM and variant-dependent enable/access behavior. It does not establish TPS65132 identity from address 0x3e. |
| Solomon mobile-driver overview, 2 pages, copyright 2020 | Useful correction to identity reasoning: p.2 explicitly lists SSD2092 as TDDI, with MIPI four-lane and I2C interfaces. Marketing selection guide, not register/command documentation. |
| bsg100 hardware inventory | Useful other-unit leads and chronology; mixes older summaries, newer corrections and unsupported generalizations. Do not import its support matrix or implementation plan. Specific conflicts are below. |

## Findings that change interpretation

### Reads can change the evidence

Part 1 p.1084 describes AUXADC channel-data bit 12 as ready and cleared by a
read. This narrows the [thermal acquisition question](../../docs/hardware/mt6797-thermal-observation.md):
an independent raw AUXADC read may consume readiness, in addition to the
functional specification's AUTOSET trigger claim. Neither document establishes
that thermal measurement-register reads share that behavior. The reviewed
tables supply no complete thermal TEMPMSR acquisition-age contract. Keep the
selected thermal driver's ownership; do not add a raw reader to infer freshness.

AW9523B p.11 describes port-specific interrupt clearing by reading the affected
input port and an 8 microsecond input deglitch filter. The latter is not measured
keyboard-contact debounce. A future IRQ experiment must distinguish input
change, interrupt delivery and acknowledgement while preserving the working
[GPIO/matrix polling path](../../docs/hardware/keyboard.md).

FUSB301A register 0x13 is read-clear; device ID 0x01 and status/type 0x11/0x12
are separately described. A broad register dump could consume an attach/detach
event. P.9's eight-bit bus address corresponds to seven-bit 0x21 or 0x25; this
is consistent with the project's two observed 0x25 clients, not proof of their
physical-port assignment. P.10's 0x12 device ID agrees with retained probe logs.

BQ25896 REG0C preserves fault history until read; the first read returns latched
faults and a second returns current status, except NTC_FAULT is always current.
P.31 excludes REG0C from multi-read/multi-write. An observer must preserve both
meaning and driver ownership, rather than label a destructive dump passive.

### Power control includes more than selector values

DA921x pp.26-27 describes A/B selection, GPI control, voltage maxima, track mode
and ramping; p.46 documents V_LOCK. The voltage tables corroborate the existing
0.30 V + 10 mV/selector mapping, including selector 70 as nominal 1.00 V. That
is a decoder result, not a measurement. Track mode can bypass Buck A selectors,
and limits/GPI choices affect output control. These are checks for future
production ownership, not evidence that the current read-only provider is wrong
or that a different DA921x driver can be substituted.

BQ25896 p.31 says a write transitions default mode into host mode, while
watchdog expiry resets selected configuration with explicit exceptions.
Consequently a same-value write need not be behavior-neutral. Driver probe,
watchdog handling, boost exclusion and failure cleanup belong in the already
planned charger/VBUS contract; the datasheet alone cannot supply safe battery
parameters or justify enabling OTG.

TPS65132 separates volatile voltage writes from EEPROM programming. Control
0xff bit 7 requests EEPROM programming; bit 0 selects the read bank. P.17
specifies a programming interval and finite endurance. Pp.16-17 also distinguish
variant-dependent power-down and I2C accessibility. Thus matching two voltage
registers and an address cannot prove compatible startup/shutdown behavior.
An unidentified bias chip should not receive a reset, EEPROM command or guessed
compatible as an identity test.

### SSD2092 is not categorically touch-only

The Solomon selection guide classifies SSD2092 as an integrated touch/display
controller (TDDI), with 1080RGB x 2280 capacity. The community inventory's claim
that the vendor name denotes only touch cannot exclude a shared display IC.
Conversely this brochure cannot prove the named Gemini contains that part, nor
can its catalog dimensions replace this device's 1080x2160 panel geometry.
The [existing panel contradiction](../../docs/hardware/gemini-gemian-baseline.md)
remains unresolved: this unit's active NVT touch and software-selected NT36672
LCM differ from the other unit's reported Solomon evidence. A future identity
experiment must separately attribute display DCS and touch-bus responses.

### More detailed tables still contain errors and omissions

Part 1 p.288 labels R19_LOCK as controlling region 1 and R23_LOCK as controlling
region 20; the field names and prose disagree. These are visible source errors,
not extraction artifacts. EMI range/policy descriptions and searches did not
establish priority for overlapping regions 18/23 or CONSYS master-domain
assignment. Existing [Wi-Fi ownership gates](../../docs/hardware/mt6797-wifi.md)
therefore remain. The already used ADDR2 bit-32 description on pp.418-419 does
not establish the bus alias or DMA mask.

Part 2 pp.704-706 distinguishes PWM shadow commit, update source, frame sync,
polarity, manual/automatic mode and double buffering. This gives a concrete
way to audit a future no-visible-change PWM result before guessing brightness
values. Its 26 MHz formula is a documentary assumption to compare with the
selected clock tree, not proof of the live parent. No PWM write is proposed.

## Secondary-source conflicts

The bsg100 snapshot names Mali T860, whereas the functional specification and
Gemian inventory name T880; retains RT5735 as the CPU-regulator dependency
despite this project's legacy DA921x observations; and labels AW9523 absent
based on Linux 6.6, which cannot override this project's later pinned upstream
provider and working matrix path. It says no bus has a device at 0x53 in the
charger discussion but elsewhere describes a later active 0x53 touchscreen.
Those observations need their individual boot/time/reset contexts.

Its blanket mainlined thermal/support labels do not establish this project's
protection, suspend, cpufreq or native display support. Its fixed-role USB
success is a lead, not evidence that CC/VBUS ownership can be skipped here.
The missing linked logs and source revisions are required before adopting new
cross-unit claims. Existing earlier bsg100 comparisons retain their own pinned
provenance; this downloaded moving-branch file does not replace them.

## Outcome and follow-up

At review time the collection narrowed diagnostics, display identity and
power/IRQ contracts without resolving the then-open Wi-Fi EMI blocker.
Subsequent work is linked in the reconciliation above. Current follow-up
belongs in the [roadmap](../../docs/ROADMAP.md); this restoration changes no
implementation, manifest, profile or hardware-support claim.

## Validation

All 17 supplied size/hash checks passed. `git diff --check` and
`./scripts/check-repository` passed, including changed/untracked documentation
and source metadata. Kernel build, checkpatch, DT schemas and device tests were
not run for this documentation-only assessment. Earlier uncommitted review work
was preserved; nothing was committed or pushed.
