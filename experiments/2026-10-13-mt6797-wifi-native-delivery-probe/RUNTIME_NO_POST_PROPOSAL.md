# Runtime-only success-post-read comparison — proposed, not selected

ROOT requested this small host-first comparison after [CCMP4](CCMP4_RESULT.md).
Repeated post-CLOSED selected/header mismatches and a public gen3 single-packet
source difference motivate a **read-sequence hypothesis test**, not a proven
FIFO-pop fix. No controller queue-advance trigger is certified. No profile,
series, configuration, receipt, package, build or device action is selected by
this proposal. Firmware analysis remains held pending this review.

## Exact body and source for ROOT review

[0195 format-patch](../../patches/proposals/0195-wifi-mt6797-omit-MAC-runtime-success-post-read.patch)
is one logical change atop C4 source `b5969e62f02486f70fec2f202e21ec3e724286d9`.
Review source `85d1d6212d24f8c1d53050dcc4be7060820c06af`; only `hif.c`, `hif.h`
and the two `mac.c` call sites change: 36 additions/12 deletions, including call
alignment. It applies cleanly to the actual prepared C4 tree (`git apply --check`).

| Pin | SHA256 |
|---|---|
| Format-patch | `7a1d50eb6aa7ddb02066e2255a2e1547b88b7c48b9f9bc664673c321eafdee4f` |
| Diff body, first `diff --git` through before format-patch trailer | `a3a9f2f964d94c9d5aaacedce77e0180bf8cca6d679b9a1e72392646891f03aa` |
| Child hif.c | `904ee916416359987b6168a6d84a8fbf155fcfabc599a1789609dbd130d83790` |
| Child hif.h | `55cea74081c83b41221b72246494a42548d4f30857fbe9def9116597ed4ebe11` |
| Child mac.c | `fdc2d7fb6391e64b1e3d6bda0d75a6f7e326241091da48f9611d328630617d9a` |
| Unchanged prepared C4 mt6797-consys.c | `76e114641b11c2e0ff5ca72be7b36cadbbe51dec1f92a2abd6b45268deab8053` |

Internal synthetic non-certifying archive, no invented DCO. Checkpatch reports
only the missing truthful sign-off: one error, zero warnings/checks. This is not
an upstream-ready patch or a hardware result.

## Small explicit API split, no cache or new observer

The original `mt6797_hif_receive_packet()` signature remains and always selects
the existing success post-WRPLR acquisition. The new
`mt6797_hif_receive_runtime_packet()` selects no post acquisition. Both call the
same private receive implementation; one internal boolean surrounds only the
existing post-read block. No caller-configurable framework or retained state.

Only MAC join and scan switch to the new entry point. Every successful runtime
receive still performs pre-WRPLR sample, selected-port FIFO transfer, guard,
strict selected/header equality, type extraction, caller copy and logical-byte
publication. It omits exactly **two transport operations: one setup and one read
for one logical WRPLR acquisition**, not two logical-register acquisitions.
`post_valid=false/post_wrplr=0` means unread, not empty or unchanged hardware.

Every failure before that block retains its previous operation sequence,
poison/absence/no-copy behavior and failure-only staged hint. A failure of the
omitted post acquisition is no longer possible for the runtime entry point;
that intentional difference must not be called identical I/O-fault coverage.
The boot entry point retains those two fault sites and their fail-stop behavior.

MAC's only post-field references are in its existing refusal log; runtime
failures already bypass the success post-read. MAC does not inspect those
fields on success. Per-port arbitration remains port0 then port1 with fresh
full-DWORD pre samples: this comparison does **not** test or fix all possible
unmatched-sample cases. The selected halfword, port, transfer span, absolute
deadlines, locks and every other read remain unchanged.

## Boot drain invariant preserved exactly

`mt6797_consys_drain_boot_events()` still calls the original receive API.
On success it takes `last=rx.post_wrplr` (C4 consys line905), validates only
admitted boot events, then stops at `last==0`, refuses an opposite-port pending
length, or continues its existing finite loop (lines939–943). On EAGAIN it
instead checks the pre sample. The reader, post metadata, all branch logic and
boot-event budget stay byte-unchanged. No stale pre sample substitutes for the
post metadata, no extra drain read and no new interpretation of queue advance.
Capability and download paths and the standalone observer are also unchanged.

## Why this is a comparison, not a certified explanation

Public gen3 source pinned at `59e00a9144d782e148332009a835b99c43382467`,
`nic/nic_rx.c:2826–2908`, non-enhanced `nicRxReadBuffer`, reads WRPLR once,
chooses port0 if low nonzero else port1, reads the selected FIFO and checks RXD
byte count, without a success post-peek. It too reads both halfwords while
serving only one port. Its response waiter also polls a full DWORD for a single
requested half. These source facts do not certify the AP bridge's pop/latch
behavior or establish the active vendor configuration.

C4 retained phase counters establish 575 successful receives within the four
reported diagnostic phases: 512 sample +59 drain +4 CLOSED. By the exact C4
source, each success passes through its post read; this is a path/count
inference, **not 575 individually logged pre/post value pairs**. Those pairs
are unavailable in the retained runtime log. Many successful transfers must
constrain any claim that every observation invariably loses a queue entry.
Even equal pre/post numbers would not establish no advance: equal-length
packets or new pushes can match. The refused attempt skips its own post read,
but earlier successful reads could still have disturbed pairing. Nothing here
proves or excludes that possibility or explains the repeated difference48.

## Focused actual-source tests

`tests/runtime-no-post-test.py PARENT CHILD PREPARED_C4` reuses the existing HIF
compiler, actual source and transport mock under ASan/UBSan. It pins the C4
parent, matches it to prepared source, reverses the exact limited source delta,
checks both MAC calls and the original boot-drain dependency. No kernel build.

- Boot reader success/negative/every-I/O-fault tables unchanged, both ports,
  including a nonzero synthetic post DWORD; its publication and poison remain.
- Ten runtime success cases (both ports, lengths4/76/80/449/2352) show exactly
  two fewer transport operations with unchanged accepted bytes/type/length.
- 1638 common runtime negative/fault cases match, including length/equality,
  capacity, all reachable transport fault sites, refusal hint, no caller copy,
  poison and poisoned second-call no-I/O. Twenty parent-only injected faults
  are explicitly the deleted two operations over ten success cases.
- All other driver files are byte-identical. MAC changes reverse exactly after
  name/alignment restoration. No budget, RX/PN/key/cleanup implementation changes.

These mocks do not model a queued-length FIFO or prove a hardware pop trigger.
They establish the proposed operation/publication contract, not radio support.

## Proposed one-trial protocol and decision branches

**Review first:** ROOT reviews exact patch/body/child source, preserved boot
drain and both MAC call sites. Only after admission would a fresh named profile
select exact C4 ordered689 +0195, with the same26 fragments and finite protocol.
All existing selected profiles/series remain pinned and unchanged at this stage.
No selection/build/assembly-permission detour is performed or requested here.

Any later build must use clean pushed reviewed inputs and ordinary Buildbox
provenance, then a fresh real composition receipt and receipt-bound tools;
current C4 receipt is not deployable proof of this proposed source. ROOT alone
installs, verifies live candidate/boot, runs one capture/session, preserves and
seals evidence, quiesces helpers and performs the one reviewed return. Physical
boot2 selection remains the owner handoff. No unchanged-artifact retry.

**Hypothesis:** runtime-only removal of the unused success post acquisition may
change the repeated post-CLOSED selected/header refusal/cleanup outcome. The
unique observation is the first finite run of this exact source-controlled
delta, not a new register measurement. Compare existing refusal, phase, TX-done,
debt and cleanup scalars with C4, and retain the independent network verdict.
Both scan and join use this policy, so a change cannot uniquely localize cause
to post-CLOSED activity or a particular earlier acquisition.

Keep inherited all-RX512/1MiB/delivery64/wall10s-or-lower, grant/deadline bounds,
disable fence, drain budgets, checked stable-PTK delivery, normal DHCP/ping3/3/
fresh boot-bound SSH ACK requirements, lifecycle/no-reuse and one-return limits.
No unchecked normal RX, GTK RX, rekey, PN bypass, parser acceptance change,
register write, post-failure peek, aggregation walk or additional hardware effect.

- Same mismatch persists: removal is insufficient; hypothesis weakens. Preserve
  exact lengths/hint/phase/timing without subtract48 or another unreviewed retry.
- Healthy cleanup/no mismatch: supports sensitivity to this sequence change,
  not a certified pop mechanism, producer repair or reliable maintained Wi-Fi.
  One run and changed timing cannot settle causality; full acceptance remains.
- Different failure or incomplete evidence: classify separately; no assumption
  of success from absent refusal or missing post metadata.
- Network succeeds/fails independently: keep real DHCP, individual ping replies,
  SSH authentication/ACK and ACTIVE duration distinct from HIF/cleanup verdicts.

No runtime outcome, next implementation or firmware scan is admitted by writing
this protocol. ROOT's exact review is the next decision boundary.
