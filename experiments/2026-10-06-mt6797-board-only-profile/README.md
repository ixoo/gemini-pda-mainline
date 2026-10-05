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
