# MT6797 EMI owner preflight

This read-only preflight narrows two premises for a future owned WLAN EMI
transaction. It makes no protection call, register write, radio request or
boot2 candidate.

In Gemian boot `636e12fb-65de-4eb3-88c8-70c3e4cec71e` (kernel `3.18.41+`),
the live GPT's `tee1` and `tee2` labels resolved to distinct, unmounted 5 MiB
partitions. Complete read-only SHA-256 of both matched
`2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`,
the exact retained image used by the [secure EMI ABI
audit](../2026-09-05-mt6797-wifi-contract/RETAINED_EMI_SECURE_ABI.md). The boot ID
was unchanged across the reads. The raw host receipt stays ignored and
mode-restricted under `artifacts/emi-writer-identity/`; no firmware bytes were
copied. This refreshes persistent slot identity for the current device state.
It does not identify the executing secure-memory image or reveal the runtime
software-lock byte.

The live Gemian `/proc/config.gz` selects `CONFIG_MTK_COMBO_GPS=y` and
`CONFIG_MTK_GPS=y`, but has `CONFIG_MTK_GPS_EMI` disabled. In the exact pinned
Gemian source commit `59e00a9144d782e148332009a835b99c43382467`,
`drivers/misc/mediatek/connectivity/gps/gps_emi.c` (SHA-256
`1809b36948cdb333a3a2fa291a9addb589f5f65382ceaa96ae6b20c6ff5aa530`)
contains an EMI region-20 request behind that disabled option. Its write to
the shared `0x10001340` remap register is also inside `#if 0`. Thus this
particular GPS EMI implementation cannot be an active Linux remap or
region-20 writer in the observed boot. This does not exclude another kernel,
secure-world or firmware writer, nor establish an exclusive mainline handoff.

The resulting decision is to retain the EMI-write refusal. Matching persistent
TEE slots and removing one apparent Linux writer do not establish effective
CONSYS master-domain routing, region-23 overlap priority, current secure lock
state or complete external-writer exclusion. The next effect-bearing candidate
needs a reviewed owner and policy with readback and retained failure behavior;
no trial protection write is justified by this preflight.

The sanitized [receipt](results/verification.json) records the exact boot,
partition sizes, hashes, live configuration and source identity.
