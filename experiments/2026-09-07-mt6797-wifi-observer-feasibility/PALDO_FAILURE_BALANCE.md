# Balance the Wi-Fi PALDO request after a failed captured probe

The selected gen3 AHB probe requests Wi-Fi PALDO before invoking the WLAN probe.
On a non-retained probe error, it calls the WLAN remove callback but does not
release PALDO. Normal removal does release PALDO after that callback succeeds.
The retained error (`-EUCLEAN`) intentionally leaves resources in place. These
are source-path facts, not a measured regulator leak on the PDA.

The [capture-only patch](patches/paldo-failure-balance/0001-wlan-balance-PALDO-after-failed-captured-probe.patch)
reuses `HifAhbRemove()` on an ordinary probe error. Successful cleanup now
performs the normal PALDO release. If removal itself fails, the probe records
the retained state and refuses another probe without a second power request.
The non-capture build keeps its original path. This is a local correction to
the vendor diagnostic; it does not define shared VCN33 ownership or change a
mainline radio candidate.

The [source receipt](results/paldo-failure-balance-sources.json) pins the exact
58-patch prepared source, one output file and patch digest. The patch passed
`git apply --check` against the retained Buildbox tree. Strict Linux 7.1.3
Checkpatch reported zero errors, warnings and checks with the existing
synthetic-sign-off and vendor CamelCase categories excluded. The
[focused native test](test-paldo-failure-balance.py) compiled the actual probe
and remove bodies with injected callbacks. Its five cases confirmed normal
failure release, retained cleanup failure and retry refusal, pre-existing
`-EUCLEAN` retention, normal success/removal and unchanged ordinary-build
behavior. No PMIC transaction, kernel boot or radio operation occurred.

The [complete Buildbox link](results/paldo-failure-balance-link.json) passed with
the patch as the 59th selected input, a validated ten-file package, zero
undefined symbols and the inherited 69 section mismatches. The linked probe
error branch calls normal removal and retains the failure if that call returns
nonzero. The first Buildbox fixture attempt exposed a test-only temporary
library-name collision when both source paths ended in `ahb_sdioLike`; the
corrected, committed fixture passed all five cases on the exact Buildbox
parent and output. No kernel input changed in that fixture correction.

This link is not a boot-candidate admission. The PALDO helper's return value
does not attest hardware success, and the physical VCN33 control contract,
shared-resource ownership, CMDQ idle state and complete Wi-Fi cycle remain open.
