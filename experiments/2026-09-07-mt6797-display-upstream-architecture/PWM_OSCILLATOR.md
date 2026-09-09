# Display PWM oscillator ownership

Retained-kernel follow-up, 2026-09-09. Offline analysis in the RE VM only;
no live device access, clock operation, brightness change or suspend/resume.
The existing two-clock/domain stop remains in force.

## Compiled path

The retained `ddp_pwm_power_on()` enables display clock ID 27 for module 16,
then, when `disp_pwm_get_cust_led()` succeeds, calls
`disp_pwm_clksource_enable()` with its returned source selector. The power-off
callback disables the display clock for that module and conditionally calls
the corresponding source-disable helper. The source enum identifies ID 27 as
`DISP_PWM`; this is separate from the source helper's operations below.

The compiled selector table at `0xffffffc000d33748` is
`39, 37, 36, 38, -1, 40, 41` for requests 0–6. Joined to the public enum,
these are ULPOSC_D8, ULPOSC_D2, UNIVPLL2_D4, ULPOSC_D3, bypass, ULPOSC_D10
and ULPOSC_D4. The source-enable/disable branches admit IDs 37 and 39–41,
not ID 38. The earlier board selector 0 therefore selects an oscillator-control
branch in this binary; this is not a fresh observation of the live selector.

`get_ulposc_base()` maps resource 0 of `mediatek,sleep`. The compatible string
was checked directly in the Image at `0xffffffc000f61b98`; the retained DTB
describes that resource at `0x10006000`, length `0x1000`.
The helpers access offset `0x458`, hence physical `0x10006458` for this DT.

| Path | Compiled register operations, interspersed with reads and delays |
| --- | --- |
| Enable | Set bit 0; set bit 1; clear bit 1; set bit 2 |
| Disable | Clear bit 2; clear bit 0 |

The public source labels these oscillator enable, reset and clock-gate bits.
The decoded helpers perform these read/modify/write operations directly and
issue barriers, rather than calling CCF to perform them. They return zero
even on the decoded mapping-failure path; a successful helper return is not
an oscillator-success witness. This establishes compiled control flow, not
execution, oscillator frequency, lock, electrical safety or ownership by every
possible consumer.

## Consequence for the next observation

A trace of CCF enable counts and parents alone cannot account for this PWM
source lifetime. The separately admitted acquisition must include attribution
of these direct oscillator operations, alongside the existing gate, ancestry,
rate-source and MM-domain requirements. Do not use this helper as a read-only
query or reproduce its writes as an observation mechanism. Current register
contents alone would also fail to identify the writer or transition lifetime.

The extra source operation does not establish a second PWM consumer clock,
nor does it justify making upstream's `mm` clock optional. Normal upstream
clock ownership must account for the oscillator and its other consumers before
the PWM driver can rely on a declared parent. The one-handle argument remains
insufficient, and no implementation or device action is admitted here.

## Reproduction

The Image and reconstructed ELF are the retained primary Gemian inputs in the
[RTC receipt](../2026-07-11-mt6351-pmic-recovery/results/rtc-binary-receipt-20260908.json).
This audit rechecked whole-Image SHA-256
`0570480c28bce1583636a240904df8da3af0b5e5b4bcc6254f5719b42bd723d0`
and byte equality with the ELF `.kernel` section. The DTB SHA-256 is
`9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9`.
Disassemble the named symbols with GNU AArch64 objdump; hash Image slices
using virtual base `0xffffffc000080000`. Ends are exclusive next-symbol
boundaries and include padding.

| Symbol | Start | End | SHA-256 |
| --- | --- | --- | --- |
| `get_ulposc_base` | `0xffffffc0005788d8` | `0xffffffc000578978` | `4b6e9953b38e8b8010994b85b8e245e6cff64f291a28e2d73ffb6db074df6ea4` |
| `disp_pwm_clksource_enable` | `0xffffffc000578bc8` | `0xffffffc000578cd8` | `4bb95551809884bb6f8ce8cf4fd7bc483139356138645f0be4bd7bfcf0b6d89f` |
| `disp_pwm_clksource_disable` | `0xffffffc000578cd8` | `0xffffffc000578d90` | `b58b2d35b48f87d1855584c03b8b7019b1b8332f5805d64d626119d035965ded` |
| `ddp_pwm_power_on` | `0xffffffc0005b6a38` | `0xffffffc0005b6aa0` | `879bb23a2e084207dee0daa5f487b5f9e4262038fd92c282a8deaa67f35cecc1` |
| `ddp_pwm_power_off` | `0xffffffc0005b69d0` | `0xffffffc0005b6a38` | `ce60fa784949e2185e533279d4c46a5095330d196a000429c94595a756fd5ff6` |

Public comparison: Gemian commit `8cfe6596a503612e3332d9c26e292a19525a7f07`,
paths below `drivers/misc/mediatek/video/`:

| Path | SHA-256 |
| --- | --- |
| `mt6797/dispsys/ddp_pwm_mux.c` | `dade939679d1ba3576ff7c15e55e00f09ee69b6ae0e9d82fd8edb5c22646a5aa` |
| `common/aal20/ddp_pwm.c` | `45208a0418a36566bbfef7589362eb10ae81e4692645de30e53c301322ef26fb` |
| `mt6797/dispsys/ddp_clkmgr.h` | `9993fe2bfdfe3c5c7e048980f8eedaa3c2128704f74a66869aa289a3262317d8` |

Only independently described facts and hashes are published; retained binaries
remain private. No current-boot identity or runtime support is claimed.
