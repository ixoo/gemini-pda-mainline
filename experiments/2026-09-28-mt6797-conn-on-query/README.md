# Confirmed CONN-ON query for the shared owner

The passive CONSYS manager is attached to a checked-OFF modern CONN domain,
but has no way to require a fresh hardware ON witness after a future runtime
resume. Generic PM can skip a provider callback when its software state already
says ON, including after an inconclusive OFF. A successful runtime-PM return
alone is therefore insufficient before MCU or HIF access.

The [single logical patch](../../patches/proposals/0034-pmdomain-mediatek-report-confirmed-opted-domain-on.patch)
adds `mtk_pm_domain_confirmed_on()` beside the existing OFF and retained-fault
queries. It reuses the provider's checked dual-status reader, refuses mixed
bits and read errors, and returns zero only when both CONN status bits are ON
and no transition fault is latched. It accepts only the opted-in direct-control
provider. A caller must keep a valid domain association and exclude concurrent
transitions; this point-in-time check is not rail, reset, remap, EMI or firmware
admission.

The named `mt6797-a53-conn-on-query-compile` profile selects the accepted A53
service and passive CONSYS foundation plus this patch in canonical order. It
has no active caller, DT change or boot2 candidate. The next retained-fault
owner transition must request the domain under held outer prerequisites,
check this query before every powered register use, and retain those
prerequisites on an inconclusive transition. Its device test must add a unique
ON-status observation and failure branches; repeating a passive image cannot
exercise this API.

This is an internal integration patch with a synthetic author and no DCO
certification or upstream-submission claim.

## Validation

The exact pushed commit `fb14a119d34af8dc119a5c2d49c2583b18af783b`
built on Buildbox with this profile. Its fetched package passed the full
inventory and checksum validator. `System.map` contains both
`mtk_pm_domain_confirmed_off` and `mtk_pm_domain_confirmed_on`, and the Gemini
DTB SHA-256 matches the prior passive CONN-domain build. See
[the build receipt](results/build.json). No device boot or Wi-Fi test was
performed for this compile-only profile.
