# After C10: BSS address control is not yet a retirement contract

[C10](CCMP10_RESULT.md) passed its finite protected lifetime. This follow-up
resolved the two exact BSS active/inactive implementations left by the
[key-retirement review](KEY_RETIREMENT_SOURCE_REVIEW.md). Their complete visible
bodies assemble address fields and an enable bit, then perform paired register
stores. Neither body supplies an explicit queue walk, completion wait or
key-generation acknowledgement. The registers' implicit effects and ordering
against already queued frames remain unknown. No key reuse or new candidate.

## Bounded observation and validation

The sole laptop custodian used the already reviewed read-only stock get_oid
route, on independently verified changed-boot Gemian after C10 recovery.
Three separately specified observations ran once each: a fixed dispatch anchor
and two pointer words (3 queries); two fixed 64-byte prefixes behind those
same guards (35); then two continuations chosen from the visible branch targets
and known adjacent entry boundary (51). Each enforced strict boot/kernel/firmware
file/driver/ABI checks, successful status, exact eight-byte response, address
and OID echo, sentinel and buffer-padding checks. No unlock, setter, mode/key/
radio/partition write, retry or alternative endpoint. Every postflight confirmed
unchanged Gemian boot `2e2d8be5-54d4-4d99-a40b-91e005d19c1c`.

The response marshalling/allowlist fixtures passed 26, 250 and 362 cases.
The private helpers differ from the consumed reviewed readers only in fixed
boot/allowlist/count/guard identities and descriptions. Existing 30/60-second
probe limits were retained; C10 diagnostic limits were not changed.
Successful reads are source observations, not a Wi-Fi operational test.

All binary interpretation remained in the RE VM. The first decode narrowed
each 64-byte cap to a complete 62-byte instruction prefix. Their missing valid
paths were then observed under separately stated final caps of 172 and 148
bytes; no automatic window expansion or recursive following. The original
captures were checked by digest and combined under unchanged boot/file/pointer
guards. A narrow dispatch anchor does not attest the entire live firmware.

| Boundary | Complete visible result | Remaining limit |
| --- | --- | --- |
| First BSS callback | 61 instructions, index range below 5, six address bytes plus enable bit, two selected word stores, return. | Peripheral effects and shared-RX ordering unknown. |
| Second BSS callback | 52 instructions, index range below 4, the same address/enable shape, two selected word stores, return. | No key-incarnation or queued-frame attribution established. |
| Control flow | No gaps, all direct branch targets inside their fixed bodies, no backward branches or calls; both end in return. | This is local-body containment, not a model of peripheral effects or whole firmware. |

The frozen decoder retains two byte-extend flags per body. Those exact operand
shapes were independently validated in the existing 64-vector addendum; the
flags were not suppressed. New control-flow checks use the existing decoded
records without acquiring or decoding further bytes. Raw code, captured words,
addresses and private analysis records are not published here.

## Implementation consequence

Keep the demonstrated mask-only initial-PTK path as a finite baseline. C10's
stage-3 cleanup and these BSS helpers do not justify resetting PN, accepting
stale events or recycling PTK/GTK slots. A possible peripheral eligibility
change is not by itself a demonstrated purge of already queued plaintext.
There is no claim that firmware retirement is impossible or that these writes
have no relevant hardware side effect.

The precise missing capability for healthy reuse is a source-supported way to
stop old receive production and retire or distinguish every firmware/HIF frame
that could survive a key replacement, with an attributable completion boundary.
The inherited untyped key event and returned command pages cannot provide that
boundary. A future queue-drain, purge or reset proposal must establish its
actual resource ownership and completion semantics before implementation.
No arbitrary register operation or elapsed-time workaround is selected here.

In parallel scope, the ordinary per-frame integrity/PN and PTK/GTK attribution
contract remains required. The [existing RX contract](CCMP_RX_CONTRACT_REVIEW.md)
plus C10 establish layout/host rejection and positive metadata availability;
they do not prove firmware MIC-error attribution or key incarnation. Missing
metadata must remain a rejection. No alternate crypto route has been selected
without first resolving or documenting its exact missing firmware capability.

After those contracts, the [lifecycle design](../2026-10-07-mt6797-wifi-phase-b-join/REUSABLE_LIFECYCLE_DESIGN.md)
still requires firmware/resource cleanup and pinned mac80211 station/interface-
GTK teardown before healthy re-arm, with permanent fatal poison. Two healthy
lifetimes and the minimal-profile ten-minute SSH acceptance remain untested.
This observation changes no driver source, profile, deadline or candidate.

## Preservation

[Sanitized scalars](results/post-ccmp10-key-ownership-scalars.json) retain scope,
counts, validation and limits. The 26-entry private VM bundle was independently
verified against manifest SHA-256
`51e476adf1b6fef1abdeb903a780dd87827d012f9d1297150eda8ae83032fce2`;
archive SHA-256
`86bd4b8ac542e90352604d36b5ea97eca69cb32aa9702344dc727610f7f2730d`.
Decoder processes were quiescent. All three read-only probes completed normally;
no recovery was needed. Device remains in verified Gemian; C10 is installed but
consumed, and no physical action is pending.
