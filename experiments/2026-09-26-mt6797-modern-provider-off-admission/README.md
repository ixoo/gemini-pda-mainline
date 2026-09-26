# MT6797 child-domain initial-OFF admission, compile-only

The pinned Linux 7.1.3 child-domain provider creates only DT-described
domains, avoiding the legacy provider's unconditional registration of other
MT6797 islands. Its existing `KEEP_DEFAULT_OFF` branch nevertheless publishes
a domain as OFF after an ON warning, and its status helper ignores read errors
and treats mixed dual-status bits as OFF. This is unsafe as the initial
admission rule for CONN. The exact source comparison is in the
[integration gate](../2026-09-26-mt6797-conn-spm-register-control/README.md#child-domain-provider-comparison).

The [single format-patch](../../patches/proposals/0008-pmdomain-mediatek-require-confirmed-initial-off.patch)
adds an opt-in requirement for both status registers to be readable and the
selected bits clear before `pm_genpd_init`. It refuses the flag without
`KEEP_DEFAULT_OFF`; any ON, mixed or unreadable state fails domain creation.
Existing SoCs do not select it. The isolated
`mt6797-modern-provider-compile` profile compiles the child-domain driver
against the pinned Linux 7.1.3 source without adding MT6797 data or a DT
consumer. This is source preparation, not an admitted CONN transition or
device candidate.

The next integration step must select the capability in MT6797 CONN data and
add its child binding, then address the provider's post-request cleanup,
SPM key, external rail/reset and shared EMI/remap ownership before any
effect-bearing boot. A compile result alone does not prove hardware state.
