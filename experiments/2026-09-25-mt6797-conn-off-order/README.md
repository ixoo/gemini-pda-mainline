# MT6797 CONN power-off order prerequisite

The retained Gemini kernel disables the CONN domain clock before asserting
domain reset during power-off. The existing legacy MediaTek SCPSYS callback
does those two writes in the opposite order. The source and retained-binary
attribution are in [SPM key and order](../2026-09-05-mt6797-wifi-contract/SPM_KEY_ORDER.md)
and [retained SPM attribution](../2026-09-05-mt6797-wifi-contract/RETAINED_SPM_ATTRIBUTION.md).

The [proposal](../../patches/proposals/0002-pmdomain-mediatek-conn-off-clock-before-reset.patch)
adds `MTK_SCPD_CLK_OFF_BEFORE_RESET` to the existing provider. It changes only
the ordering of those two control-register writes when a domain explicitly
selects the capability. No SoC domain selects it, and this proposal does not
add CONN domain data, a consumer, a node, a key write, or an active power
transition. The existing ordering remains the default. The patch follows the
[deferred-registration prerequisite](../2026-09-05-mt6797-wifi-contract/DEFERRED_REGISTRATION.md)
in the canonical and isolated provider-compile series.

The patch was exported from a temporary single-file Git tree based on pinned
Linux `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, whose SCPSYS file
matched the recorded SHA-256
`9ce2b2c95a38bc4c7b801aff9b7c26da2dc8ec2e3fd34199adaedf1db3007226`.
After applying the deferred-registration patch, the new patch applied and
reverse-applied cleanly. A one-time host fixture compiled the actual modified
`scpsys_power_off()` function with synthetic register accessors. It observed
five writes in both cases: default `isolation, reset, clock-disable, power-1,
power-2`; opt-in `isolation, clock-disable, reset, power-1, power-2`. Both
finished with the same control value. This checks callback ordering, not
hardware operation, partial-failure recovery, or provider lifetime.

The proposal is an internal compile experiment with synthetic authorship and
no DCO sign-off. It is not an upstream submission or a boot candidate. A real
CONN owner still needs shared SPM key authority, rails, reset, confirmed-state
and failure retention before this flag can be selected. The first complete
firmware load also needs reserved EMI ownership; this patch does not permit
firmware or radio effects.
