# Retained Gemian key-reset policy and observation limits

The retained boot kernel contains the one-key reset policy identified by the
[source/configuration comparison](RESET_POLICY.md). This resolves the compiled
branch for that captured kernel. It does not establish the current device's
boot identity, register state, or physical long-press behavior.

## Identity and method

The [receipt](results/reset-policy-binary.json) pins the retained boot image,
decompressed Image, reconstructed ELF, instruction spans and table entries.
Their complete file hashes match the identities established by the
[RTC binary audit](../2026-07-11-mt6351-pmic-recovery/results/rtc-binary-audit-20260908.md#identity-and-method).
The ELF's complete `.kernel` section equals the 20,013,248-byte Image.
Every instruction word in the seven recorded spans was also compared with
that Image; the keypad-probe span is only the four-byte callsite, not the
whole function. Unlabelled instructions beyond the reset helper's last branch
are excluded from its span.

Analysis ran in the RE VM using GNU AArch64 objdump 2.42. Binary files and
private disassembly remain there. Only normalized facts and hashes are
published. No device connection, PMIC access, key event, reboot or build was
performed during this follow-up.

## Compiled policy

The keypad probe has a direct call to `long_press_reboot_function_setting()`.
That function checks the boot mode and requests:

| Boot mode | Power-key reset enable | Home-key reset enable | Timeout selector |
| --- | --- | --- | --- |
| Normal (0) | 1 | 0 | 1 |
| Factory (4), ATE factory (6) | 0 | 0 | Not updated |
| Other values | 1 | 0 | 1 |

The source's `mt_boot_common.h` names these numeric modes; its hash is in the
receipt. The normal and other branches share the same three setter calls.
Selector 1 corresponds to eleven seconds in the documented timing table from
the source comparison. The binary proves selector 1, not a measured duration.

The setter resolves a field ID through `pmu_flags_table`, using twelve bytes
per entry. Decoding the actual Image entries confirms:

| Field ID | Register | Unshifted mask | Shift |
| --- | --- | --- | --- |
| `0x256` home reset enable | `0x02b6` | 1 | 8 |
| `0x257` power reset enable | `0x02b6` | 1 | 9 |
| `0x259` duration selector | `0x02b6` | 3 | 12 |

For a matching field ID, `mt6351_set_register_value()` calls the PMIC update
helper and then returns zero without checking its result. The reset setup
caller also does not check the setters' return values. Consequently these are
compiled configuration requests, not proof of successful register updates.

## Why the existing debug read is insufficient

The compiled `store_pmic_access()` selects its register-read branch when the
nonempty input byte count is at most five. Larger input selects the register-update
branch. The old collector's single hexadecimal token of at most four bytes
is a conservative subset of the read branch; this audit does not relax it.

The read branch ignores both the integer-parser result and the return value
of `pmic_read_interface()`, then returns the supplied byte count. The latter
helper calls `pwrap_wacs2()` with write-enable zero and updates the shared
result cache only on success. On a transport error it returns without changing
the caller's cached value. `show_pmic_access()` formats that shared cache and
performs no new PMIC transaction.

A successful userspace write followed by a numeric read therefore cannot, on
its own, prove that the requested register was read successfully. The store
and show callbacks also have no lock spanning the pair; another user of the
interface could replace the shared result between them. This is a freshness
and attribution limit, separate from selecting the non-writing PMIC branch.
It does not assert that a historical captured value was wrong.

## Consequence

Do not use an unqualified `pmic_access` result to admit the live reset policy.
A future bounded observation needs attributable transport success and result
ownership, in addition to exact live-kernel identity and a reviewed register
read. No arbitrary PMIC command, full register dump or reset-field write is
introduced here. The compiled policy supports the one-key/selector-1 hypothesis;
physical timing and recovery behavior remain separate owner-present tests.
