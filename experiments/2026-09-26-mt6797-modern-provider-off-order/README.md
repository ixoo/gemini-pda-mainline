# MT6797 modern CONN OFF request order, compile-only

The [retained CONN audit](../2026-09-05-mt6797-wifi-contract/RETAINED_SPM_ATTRIBUTION.md)
establishes its OFF sequence: protection, isolation, clock-disable, domain
reset assertion, then primary and secondary power-request clears. The modern
Linux 7.1.3 direct-control provider already places clock-disable before reset;
no patch is needed for those two operations. It clears the secondary request
before the primary one, however. There is no evidence that the two request
orders are interchangeable for this island.

The [one-change patch](../../patches/proposals/0015-pmdomain-mediatek-clear-mt6797-conn-primary-first.patch)
selects primary-first clearing only for MT6797 CONN. Its selected OFF path
checks the isolation, clock-disable, reset and both request writes. A failed
write stops the remaining sequence and reaches the existing retained-fault
latch. Other domains keep their previous order and error behavior. The patch
does not change ON sequencing, shared bus protection, external rails or reset.

It follows the SPM preamble in canonical order and in the isolated
`mt6797-modern-provider-compile` profile. No MT6797 child DT node or client
is present, so no power transition or device test is selected. The accepted
A53 profile remains unchanged. Pinned checkpatch reports zero errors and
warnings. The synthetic patch author makes no DCO certification or upstream
submission.

The [Buildbox result](results/build.json) records a full ARM64 link from clean
pushed commit `b50ddddfd849fd2fa716c3fc26acc260945c5985`. The fetched
package passed its SHA-256 inventory check and contains all nine selected
patches. The modern provider, CONN domain data and fault query are linked;
the legacy provider is disabled. Neither packaged MT6797 DTB selects the
new controller. No device write or boot was performed for this result.

A hardware candidate still needs external VCN/CONMCU preparation, writer
exclusion, remap/EMI ownership and a reviewed failure lifetime. This build
does not prove the OFF sequence on hardware.
