# Retain the normal-command session after capability

The [last device boot](../2026-10-01-mt6797-port0-header/results/runtime-1.json)
proved a 124-byte capability reply on port 1 and identified one port-0 debug
event. It did not send a calibration or domain command. The current HIF
created its normal TC4 transaction on the capability query's stack, so the
25 remaining pages and received phase disappeared on return. The shared INIT
sequence bitmap survived, but a later command could not safely continue the
same normal ledger. The [source-bounded selected initialization](../2026-09-05-mt6797-wifi-contract/NORMAL_COMMAND.md)
needs up to 21 pages including capability.

[Patch 0058](../../patches/proposals/0058-wifi-mediatek-retain-normal-command-state.patch)
moves that existing transaction into the serialized HIF object. Capability
admission still starts once with the selected 26-page normal quota, distinct
from INIT TC4. A valid reply leaves `CAP_RECEIVED`, 25 free pages and the
original shared sequence history. Any HIF failure after admission poisons
both INIT and normal state. This changes no wire bytes, command order, credit count, resource
write or radio state. It does not expose a new command sender.

The [focused host test](tests/test-normal-owner.c) executes the exact patched
HIF through START, capability and the prior one-shot port-0 read. It asserts
persisted phase/credit/history after success and poisoning across the 69
capability and 29 port-0 scalar faults, stale/malformed responses and deadline
refusals. The [host receipt](results/host-validation.json) pins the source and
patch identities. Linux checkpatch and `git apply --check` ran against the
exact prepared predecessor source. The selected profile composes this one
patch after the previously booted port-0-header series; no historical profile
was changed.

A later owner must serialize the actual source-ordered power, domain and NVRAM
submissions against this ledger and derive regulatory restrictions through
cfg80211. The vendor's fallback country tables are not mainline policy. This
patch alone has no reason for another device boot. A Buildbox compile is the
next validation gate; it is not hardware support.
