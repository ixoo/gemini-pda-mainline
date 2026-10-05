# C3 timing retry protocol (C3-2)

Status: draft for coordinator review, 2026-10-06. No candidate is composed and
no device action has been taken under this protocol.

The first attempt under [PROTOCOL.md](PROTOCOL.md) is consumed; its result is
in [RUNTIME_1.md](RUNTIME_1.md). This is a new experiment with a new kernel
artifact and a new boot. It is not a retry within that boot, and the old
candidate is not reused.

## Hypothesis and unique observation

H1: the ROM answers WMT Bluetooth function-on, and then HCI Reset on task 0,
without a ROM patch or RF calibration, when the host waits as long as the
vendor does. The first attempt is undecided: it received the STP ACK of
BT-on but no event within 600 ms.

The decision-changing difference is the wait. The vendor waits
`WMT_LIB_RX_TIMEOUT` = 2000 ms for every WMT event, and its header notes that
Bluetooth function-on alone can take about 830 ms on some phones. Source:
`wmt_lib.h` line 70 in the public
[vendor kernel at `c5b0be85`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/include/wmt_lib.h#L70).
The unique observation is whether a function-on event arrives within 2 s.

## Artifact

| Item | Value |
| --- | --- |
| Profile | `mt6797-a53-wifi-common-init-compile` |
| Commit | `025b26676330f2e29666a9a3ab2fa3e8e7ec5242` |
| Package inventory | `adda8f2de1ec2a3ad157676eb2103673e8e79d5f711d862a30aef829c62ca111` |
| Release | `7.1.3-gemini-a53-wmt-versions`, inherited from the profile fragments |
| Built board DTB | `07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734` |
| Builder | buildbox-3; remote validation, fetch and local checksums passed |

The release string matches the consumed C3 candidate and the WMT-versions
parent. Identity checks must therefore use the candidate's boot2 SHA-256 and
the package inventory, not the release alone. This package adds patches
0111–0113 to the C3 profile. With the common-init flag absent, 0111–0112 add
no runtime action; 0113 only changes the Bluetooth waits.

## Candidate composition

Compose from the booted WMT-versions parent, as for C3. Change only the
kernel image and these DT properties. Resolve phandles from the booted DT; keep
the RAM root byte-identical to the parent, as C3 did.

| Node | Change |
| --- | --- |
| CONSYS | Remove `mediatek,one-shot-wmt-identity-capture`. Add `mediatek,one-shot-wmt-negotiate` and `mediatek,one-shot-bt-reset`. |
| CONSYS | Append the `afe` region, `0x180b6000` size `0x100`, as the tenth `reg`/`reg-names` entry. |
| CONSYS | Add `vcn33-bt-supply` pointing at the new VCN33-BT node. |
| CONSYS | Must not contain `mediatek,one-shot-wmt-common-init` or `mediatek,coex-antenna-mode`. |
| MT6351 regulators | Add `ldo-vcn33-bt` with `regulator-name = "vcn33-bt"` and nothing else. |
| WLAN child | Keep `status = "disabled"`. |

Validate the composed DTB against the CONSYS binding from this package's
source. The binding rejects the common-init flag together with the Bluetooth
flag, and rejects the Bluetooth flag without negotiation or the supply. Record
the composed DTB, boot.img and padded boot2 SHA-256 in a private receipt.

## Sequence

1. Guarded live-GPT boot2 install with full readback and clean shutdown, as for
   C3. The owner selects boot2 physically.
2. On mainline, confirm the changed boot ID, the candidate identity, USB SSH and
   the active console.
3. Preserve region 19 and prepare WMT memory exactly as in C3.
4. Write `1` once to `wmt_negotiate`. There is no second write in this boot.
5. Save `dmesg`, seal the log, run the A53 serviceability regression, and
   return to Gemian through the reviewed native recovery.

## Budgets and failure behaviour

| Stage | Wait | Budget |
| --- | --- | --- |
| Negotiation control | unchanged | 1.6 s |
| Each Bluetooth exchange | 2000 ms | 12 s for all five |

The sequence is BT-on, HCI Reset, Read Local Version, Read BD_ADDR, BT-off.
The first failure stops it. VCN33-BT is switched off only after a successful
BT-off; after any failure it stays on, with CONSYS power and clocks, until the
reviewed recovery. There is no retry, no ROM patch, calibration, sleep, wake,
WLAN start or scan. The raw replies, including the address, stay in the
private log.

## Pass predicates and evidence

- Control: `one-shot WMT negotiation: result=0`, with the C3 wire counters.
- H1: `one-shot BT H1: result=0 completed=5/5`.
- Report the per-step result lines, the link counters, the regression and
  recovery outcome, and the sealed-log SHA-256. Do not report the address.

## Decision branches

- **Negotiation fails.** A regression of the validated control; stop, and the
  Bluetooth result is void.
- **All five steps pass.** H1 and H2 hold within the vendor wait. Bluetooth can
  proceed ahead of common init.
- **BT-on passes, HCI Reset fails.** Inspect task-0 delivery and sequencing
  offline.
- **BT-on times out at 2 s.** H1 is not demonstrated. A 2 s timeout still does
  not prove that BT-on depends on the ROM patch. The next Bluetooth attempt
  follows common initialization, which the vendor always runs first.
- **BT-on returns an unexpected event.** Keep the bytes private and decode them
  offline before any further boot.
- Unexpected heat, power or recovery behaviour: follow the stop rules in
  [SAFETY.md](../../docs/SAFETY.md).
