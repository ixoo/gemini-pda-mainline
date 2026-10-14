# R32 versus CCMP3 — retained key-session and submission audit, source only

This bounded audit changes no driver or device behavior and performs no binary/
firmware search. It compares the public selected inputs and retained sanitized
records, not private peer/key bytes. It does not establish normal-mode Group1
availability, firmware replay/integrity, old-key retirement or maintained support.

## Inputs and reproducible source boundary

[Runtime32](../2026-10-07-mt6797-wifi-phase-b-join/RUNTIME_32_RESULT.md) used
input `7fa36c01db2deb27b55d0d77bc8279dc62b140b3`,
[candidate31](../2026-10-07-mt6797-wifi-phase-b-join/results/candidate-31.json),
boot `869f4bdf-1f54-48d3-8076-224f4910f80e`; selected explicit series has678 patches.
CCMP3 input47a23e6a selected688, approved sourcee1ec/MAC261a; see its
[receipt](results/ccmp-stable-monitor-candidate-3.json) and [result](CCMP3_RESULT.md).

The input7fa selected series is an exact prefix of CCMP3's selected series. In
a separate regenerable source-review worktree, reverse-application of the ten
successors0180/0181/0185/0187/0188/0189/0190/0191/0192/0193 reproduced that driver
source boundary without modifying either frozen author/prepared source or
building a kernel. Reconstructed R32-boundary MAC SHA256:
`2d7e5a33fa7cf3087332ba68a012a28280955feabe350e73ec0e7537d1e8d874`.
This is source reconstruction from pinned selected patches, not a new hardware
sample or independent measurement of old runtime memory.

Retained R32 join-records SHA256
`53715071412e341e482ff06820b99d31f898074bedca6f6ea03d3386e9a5b0fd`
matches its published record pin. Complete supplicant log metadata reports
26364B/SHA256 `d3de9575f9f1aa4107d893a55be9bf2f60925f224c603253580e884d979c4970`,
one PTK install, one GTK install, key-negotiation and connection. No raw logs,
key/peer bytes or private provenance are published here.

## Shared key-session conditions versus host differences

Both leaf configurations request RSN/WPA-PSK/pairwiseCCMP/groupCCMP/PMFoff.
R32's one-shot leaf at tools21066579 lacks the later explicit disabled-network/
select_network/autoconnect0 lifecycle controls; CCMP3 has those controls and
one admitted cycle. This is not a controlled single-variable producer experiment.

The original ADD_KEY predicate is unchanged: same vif/running/active/configured/
RSN/healthy/deadline and whole-credit conditions; only CCMP16-byte key, PTK
index0 with matching station, one initial PTK before one GTK, GTK index0–3. Both
observed sequences show peer-ready23, activation24, PTK command25/first owned
event/credit, then GTK command26/second event/credit. Those events/credits are
provisional attribution/command consumption, not typed key-generation or hardware
installation/retirement certification. R32's observed first group frame names
keyid1; CCMP3's supplied scalars do not establish its actual GTK index. No claim
is made that session peers, PTK/GTK bytes, replay state or all runtime inputs
were identical.

The key payload encoder and HIF key wrapper are source-identical. CMD0x07 sends
the same add/pairwise/type/index/cipher4/key-length16 encoding, with RSC bytes
left zero in both. The new host PN seed is not transmitted as a new firmware
RSC or Group1-request field. Payload-function SHA256:
`15c00d9f72c41c92d4e2062a9f8c50844ec6ea223796d4d5e5787b85e6df6f76`;
HIF key-wrapper SHA256
`859c94f86d8e0122a9e145418d22a89cbd8e5c3c48e87baca6bfd9e3424dcb9d`.

CCMP3 adds host station/key cookies, first-event waiting, host PN/epoch checks,
authorization/standard decap, no-fallback and withdrawal synchronization. Its
SW_CRYPTO_CONTROL/RX_DECAP_OFFLOAD/explicit suite registration differs from the
older host capabilities. Those facts must not be presented as identical crypto
policy or compiled binaries, or as firmware G1/replay guarantees.

## Firmware-visible submissions and retained observations

Source comparison verified identical HIF wrappers for filter0x0a, BSS0x12,
station0x13, key0x07, station removal0x14, channel privilege0x1c, and management/
security/data TX; six corresponding filter/BSS/station/key/channel/remove payload
encoders are also identical. That preserves field construction, **not equality
of every private runtime argument or command timing**. No normal-mode PN-enable
request was identified in these compared submissions.

The data-phase opener is source-identical: despite its release_channel name it
submits **no** channel-abort command at GTK credit. Both keep the channel grant
through data; healthy cleanup stage1 returns it. Thus the CCMP3 gap is not
explained by assuming the ordinary path already aborts the grant at key install.

Concrete added monitor submissions: CMD0xfc,16-byte payload, enable1 then
disable0, channel40, band/SCO/width/S1/S2/reserved bytes zero, through the existing
TC4 owner. R32 selected source has no monitor submission; CCMP3 records the one
ARM/ACTIVE/DISABLE/CLOSED sequence after both initial key credits. Host submission/
budget/decoder/lifetime controls and session timing differ too: this comparison
does **not** prove monitor toggling alone causes Group1 or the post-CLOSED fault.

R32 received60 delivered frames (33 unicast/27 group), all Group4-only/GROUP_VLD8,
then healthy deauth TX-done and credited key/station/channel cleanup. CCMP3's11
queued frames passed the strict Group1+Group4/PTK admission while monitor-active;
its ordinary group1 footer zero counters are not a normal-mode availability
sample. Group RX remains withheld, and post-CLOSED cleanup faulted before deauth
TX-done was observed. Different delivery denominators cannot be converted into
a firmware-wide availability probability or proof of a safe normal RX path.

## Decision-changing conclusion and limits

The retained evidence supports initial-key/wire-shape comparison and identifies
the monitor command pair as a concrete mode difference. It does **not** resolve
normal producer/PN output or packet/key-generation ownership. No broader source
or new RE scan is authorized by this audit, and no missing ND6 chronology line
is evidence of absent deauth or that CLOSED alone caused a failure.

A future normal-mode design still needs admitted direct evidence of compatible
per-frame PN/context output and firmware integrity/epoch-retirement contracts.
One pre-arm monitor check cannot substitute for those per-frame checks; no
unchecked delivery, generic replay floor, GTK/rekey/reuse or maintained-mode run
is proposed. The reviewed [failure-only transport hint](REFUSED_TYPE_REVIEW.md)
is a separate question and grants no producer/crypto/lifetime admission.
