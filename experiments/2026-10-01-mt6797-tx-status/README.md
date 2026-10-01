# MT6797 returned-page status observation

The [configuration boot](../2026-10-01-mt6797-regulatory-config/results/runtime-1.json)
registered a CONSYS-bound wiphy and submitted supported configuration through
PIO. Its finite debit-only TC4 ledger cannot sustain command or packet traffic.
Patch 0070 adds the missing counter observation before implementing refill.
The [initial build](results/build-1.json) passed but was superseded before a
device test to add fatal-status refusal. The [corrected build](results/build.json)
and [offline candidate](results/candidate.json) passed. There is no device
runtime result yet.

The [pinned source identities](results/sources.json) cover the selected gen3
register map, HAL, AHB access and page accountant. `hal.h:488–514` reads all
eight WTQCR words; the selected little-endian halfwords map FFA to index 14 and
CPU/TC4 to 15. `nic_tx.c:385–552` combines FFA and class completions, retaining
pending and optional pre-used debt. Neither a command reply nor CPU completion
alone is a page refund. This successor performs no refill and changes no
sequence history or software credit quota.

## One-boot protocol

Hypothesis: the selected returned-page registers yield consumable deltas for
the exclusive PIO command owner. The unique observations are WHCR, WHISR and
eight WTQCR words in three serialized snapshots: immediately after firmware
ready and before capability; after configuration; and again immediately with
no intervening normal command. The first snapshot separates retained INIT
status from the following normal submissions. It is not a quiescence proof.

The source's startup reads interrupt status and conditionally disposes of TX
counts before resetting the normal software ledger (`wlan_lib.c:514–521`).
This diagnostic reads every returned-count word even without TX_DONE, to
observe the acquisition semantics. These reads may consume interrupt and
counter state. IRQs remain disabled, packet FIFOs remain owned through WRPLR,
and no firmware-own transition or host control-register write is added.

Budget: the predecessor's one WMT/START/capability, at most eight boot-debug
packets, private-record acquisition and supported configuration sequence;
plus exactly three snapshots of ten four-byte registers. The pre-normal
acquisition and combined post-record pair each have a one-second absolute
deadline. Abnormal WHISR bit 6 or firmware-assert bit 31 stops acquisition
before any further read or command. The pair holds one HIF lock and RTNL
excludes the only later sender,
the regulatory notifier. The HIF permits one pre-normal and two post-record
attempts, with no retry or partial-snapshot replay. A transport or deadline
failure poisons the session and retains the owner. Valid-word bits distinguish
completed words; no partial record is treated as a complete snapshot.

If the first post-configuration snapshot has attributable CPU/FFA counts and
the consecutive snapshot clears them, implement conservative reconciliation
of both pools against outstanding submitted pages. This observation would
support the source's consumable-delta model, not prove all future counter
ordering. Repeated nonzero values or unexpected classes instead require a
different acquisition diagnosis before any refill. Zero counts provide no
positive consumption witness. Any failure or unexpected effect stops this
candidate. An identical boot is not authorized by a timeout or inconclusive
result.

No new RF command, interface, scan, packet DMA, interrupt enable or credit
refund is requested. Configuration effects remain those admitted by the
predecessor. Preserve the complete private log and same-boot wiphy query,
then use reviewed recovery and verify a changed Gemian boot with WLAN carrier.
Guarded boot2 installation, complete padded readback, clean shutdown and owner
physical selection remain required. No snapshot demonstrates usable Wi-Fi or
firmware application of configuration.

## Focused host validation

`tests/tx-status-test.c` includes actual patched `hif.c`, using the existing
[compatibility header](../2026-10-01-mt6797-normal-sets/tests/test-compat.h).
It verifies all ten literal register commands, output validity, the three
attempt limits, refusal of premature/competing callers, unchanged normal
credits and all 60 read/setup fault positions in pre-normal/post-record state.
Fatal interrupt flags and invalid deadlines also stop before further I/O.
Strict C11 warnings and address/undefined sanitizers pass. It neither emulates
counter consumption nor proves hardware behavior.

## Deployment handoff

The [boot2 deployment](results/deployment.json) passed the live-GPT guard,
full padded readback and clean shutdown. Exact candidate/session/capture and
reviewed recovery preflights passed. No WMT or START has been issued. The
device is off; physical boot2 selection with the console enabled is the next
owner action. Then run the one-shot capture and preserve the full private
status log and wiphy query before reviewed recovery. No watcher is armed.
