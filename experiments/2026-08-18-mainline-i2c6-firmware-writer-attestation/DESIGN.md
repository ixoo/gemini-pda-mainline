# Read-only I2C6 firmware-writer attestation design

## Boundary

This experiment answers only whether the SCP branch of Gate-6 blocker B1 is
closed at the instant Linux considers granting I2C6 access, while also
re-attesting the exact I2C6 Device-APC policy installed by the retained ATF.
It does not authorize a DA921x write or a CPU request.

The existing handoff has already established a stopped/reset DVFSP PCM. Static
analysis of the exact retained LK and ATF images established that ATF programs
I2C6 module 98 as domain-0 permission `0` (`NO_SEC`) and domain-1 permission
`3` (`FORBID`). That policy does not exclude an SCP left in domain 0. The exact
vendor SCP driver releases SCP by writing `1` to SCP configuration offset
`0x000`; its debug PC is at offset `0x0b4`. The mainline profile leaves
`CONFIG_MTK_SCP` and `CONFIG_REMOTEPROC` disabled.

## Observation

The handoff driver takes two read-only samples 10--11 ms apart before running
its established validation. Each sample contains:

- SCP configuration offsets `0x000` and `0x0b4`;
- the full Device-APC I2C6 permission word for domains 0 through 7;
- all four master-domain words; and
- the Device-APC AO control word.

The immutable samples are exposed in `firmware_writer_attestation`. The
observer itself performs zero register writes and zero I2C transfers.

## Fail-closed decision

The handoff can continue only when both SCP control samples and both PC samples
are exactly zero, every Device-APC sample is stable, and decoded I2C6 domain 0
and domain 1 remain `0` and `3`. Any other result creates a sticky handoff
fault before I2C6 can become ready. The raw values remain readable so a failed
boot still changes the next action.

A pass closes only the SCP-writer sub-branch when combined with the exact-image
static audit and the established stopped-PCM evidence. It advances the roadmap
to B2, the native one-message/two-byte transport proof. A failure leaves B1
open and distinguishes SCP activity or ambiguity from a changed Device-APC
policy.
