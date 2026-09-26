# MT6797 modern child-domain fault query, compile-only

The modern MediaTek provider's opted-in CONN domain retains the first
uncertain transition error. After a failed OFF callback, generic PM-domain
state may remain ON and skip a later ON callback. A future shared CONSYS owner
therefore needs to check the latch after resume and before every hardware use.

The [query patch](../../patches/proposals/0013-pmdomain-mediatek-expose-retained-child-domain-fault.patch)
adds `mtk_pm_domain_fault()` for a valid, attached direct-control domain. It
returns the retained error, zero when none has been latched, `-EOPNOTSUPP`
for a domain without the retention flag, and `-EINVAL` for a null or
different-provider domain. The latch uses `READ_ONCE`/`WRITE_ONCE` across the
callback and owner-query boundary. The owner must serialize runtime use and
hold a valid domain association; this query is not a transition barrier.

The patch follows the isolated [MT6797 CONN data](../2026-09-26-mt6797-modern-conn-data/README.md)
in the canonical series and the `mt6797-modern-provider-compile` profile.
No client calls it, no MT6797 child node exists, and the accepted A53 profile
is unchanged. This is not a boot2 candidate. Pinned Linux checkpatch reports
zero errors and warnings. The synthetic patch author makes no DCO claim or
upstream submission.

The [Buildbox result](results/build.json) records a full ARM64 link from clean
pushed commit `fe3016f4403175cf503b7706535a375d73ec240e`. The fetched
package passed its SHA-256 inventory check and retains all seven selected
patches. The resolved configuration builds the modern provider, not the
legacy one; `System.map` contains `mtk_pm_domain_fault` and MT6797 domain
data. Neither packaged MT6797 DTB has the new controller compatible. These
checks establish source integration and linkage, not query behavior on the
PDA. No device write or boot was performed for this result.

An owner-side failure-lifetime test needs the external VCN rail, CONMCU
reset, SPM key, shared remap/EMI and writer-exclusion contracts first;
repeatedly booting the existing passive image cannot test this API.
