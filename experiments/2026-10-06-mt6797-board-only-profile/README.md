# Experiment: MT6797 board-only compile profile

| Field | Value |
| --- | --- |
| ID | `2026-10-06-mt6797-board-only-profile` |
| Status | Compile and package checks pass; not booted |
| Profile | `mt6797-a53-board-only-compile` |
| Date | 2026-10-06 |
| Device action | None |

## Purpose

Roadmap step 3 needs a product-like configuration without diagnostics. The
`full` profile cannot build, because the canonical series holds alternative
topics. The coordinator approved this compile-only profile on 2026-10-06.

## Inputs

- **Series.** 93 patches from `series-a53-service-foundation`, in canonical
  order: positions 1–91 (infracfg resets, EINT, PMIC wrapper, MT6351 MFD,
  regulator, RTC and keys, MSDC, Gemini DT, display, USB, watchdog), plus 471
  (CPU topology DT) and 504 (infracfg reset repair).
- **Fragments.** The full service-facilities chain, unchanged, so console, USB,
  keyboard, SMP8, eMMC and the watchdog handoff in the observability fragment
  are kept, along with the existing thermal, cpufreq, cpuidle and suspend
  exclusions. One added fragment sets only the release identity.

## Checks

| Item | Value |
| --- | --- |
| Commit | `76dc9d30882ba3e19e8d28fbd34c6730915bd619` |
| Package inventory | `10a1881abee31fbe249eb5ba39dd2b101d53b87f666f3b3ce2ca41b1dcf1f085` |
| Release | `7.1.3-gemini-a53-board-only-compile` |
| Board DTB | `d4b36d3022ac9b6d71019f091b1fd216a7bf1b93db0f1e9d1020fc6372f7ea38` |
| Builder | buildbox-1 |

- Compilation, remote package validation, fetch and all local checksums pass.
  The build log has no compiler warning at all; the inherited patch-0261
  whitespace and CPU rollback warnings come from excluded patches.
- **Static symbol audit.** Of 448 symbols named in the fragments, two have no
  Kconfig definition in this tree: `DEVFREQ` and
  `COMMON_CLK_MT6797_RESET_KUNIT_TEST`. Both are requested as "is not set", so
  neither has an effect. No patch was added to satisfy a symbol.
- **Resolved-config audit.** All 445 settings requested by the merged fragment
  chain appear in the final configuration with the requested value.

## Excluded topics

The other 412 foundation patches, grouped by subject:

| Patches | Topic |
| --- | --- |
| 169 | A72 bring-up, late-CPU profile, CPU-up/down lifecycle and transaction machinery |
| 95 | DVFSP handoff, state owner, vendor writer coordination, PTP/EEM, CSPM |
| 49 | DA921x identification, kobject/uevent and I2C6 observers |
| 27 | Watchdog, ram-console and pstore diagnostics |
| 1 | Frequency observer |
| 71 | Other, mostly CPU8/CPU9 admission, provider proofs and entry ledgers |

Five excluded patches look like board support rather than diagnostics and
need review before a boot:

- 102, preserve the shared MT6797 AP-DMA owner (I2C5 keyboard path);
- 112 and 114, the legacy DA9214 binding and Gemini rail description;
- 277, the MT6797 I2C short-write contract;
- 297, watchdog locked reset status.

## Not established

Whether this configuration boots, and whether the console, USB SSH, keyboard
and eMMC services still work without the excluded patches. A boot needs a
reviewed protocol and owner approval.

## Board-services correction (2026-10-07)

The coordinator's compatibility audit showed that the exact C1-5 parent DT
cannot run on the 93-patch board kernel by disabling I2C6 alone. The old key
driver turns the 11-second reset value into 5 seconds, the GPIO66 pull, input
and Schmitt fields are missing, the RTC is not configured, and the DVFSP
handoff node and A72 methods are unsupported. This correction keeps those
services instead of dropping them. Status: profile defined; not yet built or
booted.

### Profile `mt6797-a53-board-services-compile`

- **Series.** [series-a53-board-services-compile](../../patches/series-a53-board-services-compile),
  107 patches in canonical order: the 93 board-only patches plus 14 existing
  ones. Canonical positions 594, 596 and 602 cover PMIC probe mask failure,
  IRQ-domain lifetime (the C1-adapted version) and runtime IRQ transport
  errors. 604 and 621–624 cover RTC alarm masks, wake errors, bounded counter
  reads, IRQ errors and alarm IRQ enable. 605, 606, 610 and 611 cover the power
  key: failed reads, reset-setup errors, the binding and the seconds
  conversion. 627 and 630 add the GPIO66 pull, input and Schmitt fields.
- **Excluded.** Suspend-only work (597, 598, 600, 601), the PMIC baseline
  observer (625), the EINT snapshot (631), debugfs and the reset KUnit test.
- **Application.** All 107 apply with the build's own method. No context
  prerequisite was needed: every added line of 594, 596 and 602 is present in
  the result without the omitted suspend chain.
- **Config.** One fragment adds `RTC_CLASS` and `RTC_DRV_MT6397` and keeps
  `RTC_NVMEM`, `RTC_HCTOSYS` and `RTC_SYSTOHC` off. Suspend, debugfs and
  observers stay off.

### Packaged DT versus composed DT

The package's own DTB is not the candidate DT and is not claimed serviceable.
It gives the A72 CPUs generic PSCI and lacks the C1 key and lid nodes. The
candidate DT is derived from the exact C1-5 parent DTB (SHA-256 `ce3d4d23…`)
by [board-services-dt.sh](board-services-dt.sh), which refuses any other
parent, symlinks and existing outputs. It makes exactly four edits and checks
that the decompiled difference is exactly them:

- `/i2c@1100e000`: status disabled and `access-controllers` removed;
- `/dvfsp-handoff@11015000`: status disabled;
- `/cpus/cpu@200` and `cpu@201`: status disabled as stated intent. They keep
  the custom `mediatek,mt6797-psci` method, which this kernel has no
  operations for, so the CPUs never become possible. No generic PSCI is
  substituted. The expected masks are possible, present and online 0–7, with
  offline empty.

The parent DTB is private input and is not published. The derived DTB is
reproducible: SHA-256
`0fe60b14469a94c439bbda72bf56152a4cb51108b03a56f84cb0f61a6d5deefb`.

### Schema gate: no new diagnostics, not a full schema pass

| Input | Identity |
| --- | --- |
| Selected tree | Linux 7.1.3 (`be41c068…`) plus the 107-patch series, SHA-256 `24c6a2e3…` |
| Processed schema | `dt-mk-schema` over that tree, SHA-256 `e067ef24…` (dtschema 2026.6) |
| Derived DT | `0fe60b14…` |

Compared with the parent, the derived DT adds no diagnostic. It removes only
the I2C6 "unevaluated access-controllers" error. These inherited limitations
remain and are not addressed here:

- six SPI nodes whose `mediatek,mt6797-spi` compatible is not in the SPI
  binding;
- the SCPSYS power controller's compatible list and child layout;
- both A72 CPUs' custom enable method, which is intentional;
- the DVFSP handoff compatible has no binding in this tree; the node is now
  disabled.
