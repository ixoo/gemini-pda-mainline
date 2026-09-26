# MT6797 CONN provider failure retention prerequisite

The legacy MediaTek SCPSYS ON callback releases its clock and optional supply
after an ACK, SRAM or bus-protection error, even when the power request has
already been written and OFF has not been proved. For a future initially-off
CONN domain, that cleanup could remove prerequisites from an uncertain island.

The [one-change proposal](../../patches/proposals/0003-pmdomain-mediatek-retain-failed-domain-resources.patch)
adds an opt-in failure latch to the existing provider. After an ON error past
successful clock acquisition, an opted domain keeps its supply and clock
votes, records the first error, and refuses later ON/OFF callbacks. An earlier
clock-enable error still uses that helper's partial-enable rollback, but keeps
the acquired supply vote. OFF errors also latch; the existing OFF path
already retains clock and supply votes before a confirmed OFF ACK. Domains
without the flag keep their previous cleanup behavior. The new flag requires
the existing initially-off registration capability, so a flagged domain cannot
fail during provider-probe activation.

At this patch's initial compile, no domain selected the flag, so it had no
device effect. The later isolated
[CONN domain-data proposal](../2026-09-26-mt6797-conn-domain-data/README.md)
selects it in a compile-only profile; no boot candidate does. This latch does
not acquire CONN rails, control independent CONMCU reset, enable the SPM key,
choose an EMI policy or grant a WLAN transaction. A failed OFF can leave genpd
software state ON, causing a later consumer resume to skip the power callback;
the eventual shared owner must check the latched fault before **every** use.
There is no automatic recovery or resource release from a latched fault.

The later [fault-query proposal](../../patches/proposals/0006-pmdomain-mediatek-expose-retained-domain-fault.patch)
exposes that first latched error to an attached, opted-in domain owner. It
checks that the supplied generic domain uses this SCPSYS provider, returns
`-EOPNOTSUPP` for an unflagged domain, and returns zero only when no fault has
been latched. The owner must hold a valid domain association and check after
resume and before every hardware use; a successful runtime resume alone is
not admission after a failed OFF callback. The query does not acquire rails,
release a latched fault, or make CONN activation safe. It is selected only by
the isolated provider-compile series, with no consumer or boot candidate.

The patch was exported from a temporary single-file Git tree using Linux
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c` SCPSYS source SHA-256
`9ce2b2c95a38bc4c7b801aff9b7c26da2dc8ec2e3fd34199adaedf1db3007226`
after applying the selected deferred-registration and CONN OFF-order proposals.
It replayed onto that exact predecessor with whitespace checks. Pinned upstream
`checkpatch.pl --no-tree --no-signoff` reported zero errors and warnings.
The synthetic patch author makes no DCO certification; this is an internal
integration proposal, not an upstream submission. The destination is the
MediaTek power-domain provider; delete the proposal if upstream takes an
equivalent failure-retention design or this shared owner is replaced.

The isolated `mt6797-provider-compile` series selects this patch after its
two prerequisites. Compilation can validate integration, but only a later
admitted domain and owner-controlled device protocol can test failure
retention on hardware. No boot2 candidate is admitted by this change.

## Buildbox result

`KERNEL_PROFILE=mt6797-provider-compile ./scripts/build-kernel --backend buildbox`
compiled and linked clean pushed commit
`9189676116147905aaad999de515596a6c337a25`. Buildbox applied all 17
selected patches, including this patch with SHA-256
`2ca761d5b8be64d70dc0a4ec88e9b406980a09379050f215a4853afe6f7bf824`.
The validated package inventory is
`1d6c63b992e2536793ffef6bbb9f7cf1c7468bfec7987ae76f61631792bf824d`,
under ignored `artifacts/buildbox/<commit>/`. Its provenance reports a clean
checkout, patchset SHA-256
`efcca0eaf5a812ea6dd563d5fe22f33b690192e061f6d9a62007978838c095a7`,
`CONFIG_MTK_SCPSYS=y` and `CONFIG_PM_GENERIC_DOMAINS=y`; `System.map`
contains both `scpsys_power_on` and `scpsys_power_off`. No hardware test,
domain activation or device write was performed by this build.

## Host fault-injection result

`python3 scripts/test_fault_retention.py` fetched the pinned upstream SCPSYS
source, verified its checksum, applied the three pinned provider proposals in
series order, then compiled seven extracted, unmodified C callbacks against
host-only resource and ACK spies. Four cases and 82 assertions passed: an
opted ON ACK timeout retained both clock and supply votes and refused further
callbacks; an unflagged domain performed its legacy cleanup; a second-clock
enable failure rolled back the first clock while retaining the supply vote;
and an opted OFF ACK timeout retained both votes and refused further callbacks.
The test uses synthetic registers and does not establish hardware behavior or
admit a boot2 candidate.

The later query revision adds pinned source replay for the CONN table and
query proposals and a query case that observes zero before any fault, the
retained `-ETIMEDOUT` after a failed OFF, and rejection of invalid or
unflagged domains. The host fixture passes six cases and 110 assertions. The
new patch passes pinned `checkpatch.pl --no-tree --no-signoff` with zero errors
and warnings. This remains host evidence, not a device result.
