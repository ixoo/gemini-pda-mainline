# Checked MT6797 CONN OFF query

The shared CONSYS manager cannot release external VCN rails merely because a
child's runtime suspend or unbind returned successfully. Generic PM domains
can skip a power-off callback, and the existing retained-fault query reports
no error before a callback has run. The [query patch](../../patches/proposals/0016-pmdomain-mediatek-report-confirmed-opted-domain-off.patch)
provides a narrower necessary check for the opted direct-control domain.

`mtk_pm_domain_confirmed_off()` returns zero only if the retained fault latch
is clear and both independently read power-status bits are clear. It returns
the latched fault or first status-read error, `-EBUSY` for ON or mixed status,
`-EOPNOTSUPP` for a domain without fault retention, and `-EINVAL` for a null
or different-provider domain. The caller must keep the domain association
valid and exclude concurrent transitions. This snapshot does not prove that
the OFF callback ran, that all CONSYS clients are quiescent, or that retained
firmware cannot reactivate the island. It is not by itself permission to drop
rails or reset. The future manager must retain prerequisites whenever those
other conditions are unresolved.

The patch is a format-patch from a disposable two-file snapshot of the exact
prepared Linux 7.1.3 A53 modern-provider source. It applies to that source
without changes and passes pinned `checkpatch.pl` with only the synthetic
author's missing DCO sign-off excluded. The existing A53 integration profile
now selects it after the modern provider's retained-fault query and OFF-order
patch. No consumer or effect-bearing DT child is added; the PDA should stay on
the working Gemian boot.

## Build result

Clean pushed commit `603e024db107f799c1fff78d36b1dd8c08f5c3f4`
applied all 515 selected patches and linked the full A53 kernel on Buildbox.
The fetched package passed its complete checksum inventory. The
[receipt](results/build-a53.json) pins the exact package and input digests;
`System.map` contains the new query and existing fault API. The resolved
config and all five Gemini DTBs are byte-identical to the prior A53 provider
integration package. The build establishes source linkage only. No CONN child,
shared owner, runtime caller or device transition was exercised.
