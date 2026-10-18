# Mask-only control comparison — before implementation

Status: [C10 built and privately composed](CCMP10_PREPARATION.md); no device
write or runtime result. The design below preceded implementation. [Pointer observation](POST_C9_POINTER_RESULT.md) resolved
one complete monitor callback: for Boolean arguments it writes a three-bit mask,
7 on enable and 0 on disable, to firmware address `0x800c0068`. No firmware code
is copied. Group meanings and the RX length-publication mechanism remain unproved.

A separately bounded retained-source review of the standard ACCESS_REG default
SET branch confirms its address/data store and return. This target is within
the checked normal address guard and outside special-address dispatch. The
existing HIF join sender owns serialization, fixed command encoding, sequence
retirement, one-page TC4 accounting, deadlines and fatal transport poison.
Command credit is not an independent firmware completion acknowledgement.

## Hypothesis, observation and decision branches

Hypothesis: the observed mask operation can request the metadata needed by the
existing initial-PTK checker while retaining ordinary filtering/channel state.
This could separate metadata availability from global monitor side effects.
It does not presume that the mask controls particular groups or fixes gap48.

Unique observation: one finite stable-PTK session using only the exact observed
mask values through the standard firmware command, without SET_MONITOR. Reuse
existing group-presence masks, reported-index metadata and checked-delivery
counters. No new receive read, accepted-packet interpretation, key bypass or
userspace API. Existing ordinary-frame rejection remains mandatory when PN or
other required metadata is absent.

1. Required ordinary metadata and checked protected traffic: preserve exact
   group/status/ownership observations and individual DHCP/ping/SSH results.
   This supports availability in this scope, not firmware integrity enforcement,
   GTK/rekey, key retirement, reusable lifetimes or maintained Wi-Fi.
2. Metadata absent/unsupported: record rejection; do not enable global monitor
   as a fallback or weaken PN/status/length gates during the trial.
3. Length refusal persists: preserve complete-transfer/equality/poison/no-copy.
   This comparison does not prove a producer conversion or permit subtraction.
4. Earlier timeout/different failure: classify separately; no repeated artifact,
   deadline extension, credit refund or automatic successor.
5. Healthy cleanup: record independently. One completed finite session does not
   prove pending-frame retirement or safe station/key-slot reuse.

## Exact operation and resource boundary

One default-off option, dependent on the existing stable-epoch diagnostic,
selects a new internal HIF helper. Its fixed eight-byte payload is little-endian
address `0x800c0068`, then value 7 for arm or 0 for close. CID `0xc0`, SET=1,
standard sequence/header and existing join submitter. Validation admits only
that address, length and those two complete values under the option; no generic
register interface. Reject SET_MONITOR under this option to prevent fallback.
All other profiles retain their existing command allowlist and behavior.
The comparison build refuses MAC registration without the stable-epoch runtime
arm; the existing mutually exclusive native arm cannot select another path.

The MAC selects only this helper at the existing one-arm/one-close action sites.
One fixed numeric submission line records enable/status from those operations;
it is not a firmware acknowledgement and adds no acquisition.
Keep the same state transitions, credits, 100 ms command deadline, all-RX512,
1 MiB, checked-delivery64, wall10s-or-lower, frame/grant limits and cleanup fence.
The diagnostic's state names describe host protocol phases; they do not prove
monitor mode, firmware queue drain or station/key retirement.

The exact full-word values are already exercised by the observed stock callback;
no arbitrary register/bit/value or read-modify-write is proposed. This compares
a subset of known monitor effects, with different timing/ordering still possible.
There is no proof of exclusive firmware ownership for maintained operation,
per-frame integrity or pending-format stability. The bounded profile must not
be promoted to a normal board profile on that basis. Closing the mask may still
expose the existing refusal; preserve it and fatal poison permanently.

Before any device write: review one logical patch, actual-source focused tests
and resource protocol, canonical-order named profile, clean pushed Buildbox
build/package provenance, real candidate/tool bindings, guarded boot2/full
readback and owner physical selection. One custodian and one admitted trial;
no direct stock-system write is selected. Existing reviewed preservation,
quiescence, regression and recovery gates remain required.

## Focused host validation

Test exact command/header/payload and one-page debit through the actual validator
and HIF. Reject every non-admitted address/value/length, bad sequence, outstanding
credit and transport state. Cover partial transfers and deadline boundaries,
fatal poison and no second I/O. Compile both option states and prove unchanged
parent behavior when off, including legacy SET_MONITOR and ordinary command
boundaries. Extract the actual MAC step to verify helper selection and unchanged
arm/close/credit/deadline decisions. Reuse actual RX fixtures for both ports,
observed mismatches and no-copy/poison; host tests do not prove firmware effects.

## Authored input and local host validation

[Proposal 0200](../../patches/proposals/0200-wifi-mt6797-compare-observed-mask-only-control.patch)
adds the default-off option, fixed encoder/validator and HIF helper, the existing
MAC action-site selection and the stable-arm registration gate. Its bounded
source snapshot is `0b88350`; it is not a standalone Linux revision. Other driver
files, RX/crypto/key/lifetime paths and scan/boot code remain unchanged. Global
monitor is refused only in this new mode; the option-off preprocessed HIF/MAC
fixture is byte-identical to C9.

The [actual-source test](tests/run-mask-control-test.py) passes locally with
ASan/UBSan. It covers exact address/value/length and wire header, one-page debit,
all single-bit address/payload mutations, unsupported values, short/long allocation
boundaries, stale/invalid sequence and outstanding credit. The actual HIF and
extracted MAC step pass every reachable command-write fault and expiry boundary,
fatal poison and no second I/O. Both runtime-arm flags are checked. Reversing
the exact patch recovers every parent driver file byte-for-byte. Existing receive
fixtures additionally compare 3889 boot/requested-runtime result rows and selected
reads on both ports, all five observed mismatches and injected I/O failures.
The enabled comparison produces identical receive tables. Synthetic tests
do not establish firmware effects or hardware enforcement.

Profile `mt6797-a53-wifi-ccmp-mask-control` selects C9's 694 ordered patches plus
0200. Its 26 inherited fragments are unchanged; one additional fragment enables
only the new comparison option. All existing profile definitions and named
series files are unchanged; the canonical superset appends 0200. All 33 profile
checks pass. Linux actual-source checks and kernel/package validation passed;
strict checkpatch has only the standing non-certifying DCO omission. The real
composition and remaining tooling/deployment gates are in [C10 preparation](CCMP10_PREPARATION.md).
No installation or resource write has run.

Proposal SHA-256: `933bbacc1262e7c8d827d68d3beaa4eed0a2a0ef78c023d0a777d884cf462b2c`.
