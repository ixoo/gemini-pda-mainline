# MT6797 passive scan on the known-good connection band

Status: inconclusive for management reception; the single session is completed. The fourth [2.4 GHz scan](../2026-10-01-mt6797-passive-scan/results/runtime-4.json)
completed with no management packet or BSS result. A bounded read-only
[Gemian inspection](../2026-10-01-mt6797-passive-scan/results/band-context-4.json)
found the current connection at 5200 MHz. Its stale cache does not establish
that 2.4 GHz APs are absent. This successor tests the missing band before
attributing the empty result to an RX filter or queue defect.

## Inputs and implementation

The [source receipt](results/sources.json) joins the validated record's
5 GHz support/enable offsets 197/262 with the firmware hardware-disable
capability. All three must allow 5 GHz. Private calibration supplies the
hardware gate, never regulatory authority. No raw record bytes are published.

Canonical patches 0076 and 0077 follow the exact passive-scan parent.
0076 accepts iw's inert colocated-6GHz hint while still rejecting every actual
6 GHz parameter, unsupported channel and other flag. 0077 exposes the four
non-DFS UNII-1 channels 36, 40, 44 and 48 with eight legacy OFDM rates and
20 MHz only. It carries effective cfg80211 restrictions into class-115
firmware ranges. A shared fixed channel-to-slot map joins policy, scan wire
and native management RX without shifting a mask by physical channel number.
CID 0x38 has one UNII-1 power byte: use the lowest enabled channel limit,
with all other 5 GHz groups excluded from the domains. Power bytes alone
are not channel-disable controls; firmware application and RF power remain
unmeasured. The driver retains its conservative initial 20 dBm ceiling,
ordinary cfg80211 ownership and no private country hint or custom domain.

The isolated `mt6797-a53-wifi-passive-scan-5g` profile selects the canonical
parent plus these two patches and release suffix `-gemini-a53-wifi-passive-scan-5g`.
Historical profiles stay unchanged. The implementation is original protocol
encoding from source evidence. Its synthetic archive author has no DCO
sign-off; these patches are not ready for upstream submission. The intended
destination remains the mac80211 MediaTek driver, with this experiment removed
when reviewed upstream ownership replaces the bounded implementation.

## One-boot protocol

Hypothesis: the retained firmware's completed passive-scan path can return
native management results when it includes the known-good 5200 MHz band.
The unique observation joins effective 5 GHz channel exposure, one ordinary
`iw dev wlan0 scan passive` request, matching completion, validated native
management RX and standard userspace BSS output. Do not repeat the old image
or retry in the same firmware lifetime.

The [parent protocol](../2026-10-01-mt6797-passive-scan/README.md#one-boot-protocol)
owns the WMT/START, private record, PIO ownership, accounting, regression,
evidence and recovery sequence. This child changes only the selected kernel
and its RAM-root release gate; the six verified userspace ELF files, firmware,
immutable private record and booted DTB must stay identical. Construct and
validate the exact candidate and guarded installer before deployment.
Resolve boot2 from live Gemian GPT, verify the reviewed guard, full readback
and clean shutdown; physical boot2 selection remains an owner action.

Admit at most seventeen permitted channels in one passive request, with no
SSID, probe, random address or nonzero dwell. The existing one BSS activation,
matching done event, at most 256 ticks/4096 packets, five-second scan deadline,
100 ms per receive tick, ownership checks, closing budgets and lifetime
retirement stay unchanged. No host packet TX, association, keys, DFS, IRQ
enable or packet DMA is added. A source-defined passive request does not
prove measured RF silence. Stop on the parent's safety/protocol conditions;
preserve all unique evidence before the reviewed return to changed-boot Gemian.

Decision branches:

- Matching completion and BSS output on an admitted 5 GHz channel: establish
  reception for that exact candidate and proceed to management TX/association.
- Matching completion without native frames: the tested band's absence from
  the driver is resolved; investigate RX delivery/filter behavior from new
  evidence rather than repeat an identical request.
- Refused or missing 5 GHz exposure: investigate the actual capability or
  cfg80211 gate; do not override it with a private country or raw RF command.
- Timeout, unknown wire state or ownership/accounting failure: preserve the
  complete private evidence, retire the session and follow reviewed recovery.

Raw SSIDs, peer addresses, private flags, calibration and logs remain ignored
and access-restricted. Only derived observations and sanitized candidate,
boot and deployment identities are publishable. A build is not Wi-Fi support.

## Focused validation

The two C fixtures exercise the actual selected scan, regulatory and command
headers. Compile each with `cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -I <prepared-source>/drivers/net/wireless/mediatek/mt6797 tests/<name>.c`.
They reuse the existing compatibility shim and add no firmware emulator.

Host checks pass for mixed-band requests through seventeen channels, exact
band/number fields, all byte channel values, duplicates, bounds, matching done
counts, all RX group/offset combinations and truncated extents. Policy checks
cover band boundaries, disabled/NO_IR gaps, shared UNII-1 minimum signed power,
unsupported groups, range exhaustion and zero output after refusal. Strict
checkpatch reports zero errors/checks on both patches, zero warnings on 0076
and one new-file MAINTAINERS reminder on 0077. Optional spelling/const lists
were unavailable. No new upstream maintainer claim is made.

The [clean pushed Buildbox build](results/build.json) and [offline candidate](results/candidate.json)
pass. The compiled DTB matches its predecessor; the boot image keeps the exact
previously booted DTB. The [preflight receipt](results/preflight.json) binds the
59-member RAM root, private source identities, rendered installer and session
closure. Its synthetic deployment fixture tests dependencies only. The actual
live deployment receipt and post-install capture/host preflights remain pending.
No hardware reception claim follows from these checks.

The [candidate builder](build-candidate.py) validates the exact clean build,
previous scan candidate, release-only RAM change, existing ELF hashes, boot
container and full-partition padding. The small [retarget adapter](retarget-initramfs.py)
reuses the pinned parent transform; its second output matches byte for byte.
The [installer adapter](install-passive.py) retains the reviewed GPT/device
identity guard, exact predecessor, inactive/unmounted checks, stable power,
full readback, no fresh backup and clean shutdown. Fresh ignored paths use
`artifacts/passive-scan-5g/installer-1`, `capture-1` and `session-1`.

The [capture adapter](capture-private.py), [session adapter](passive-session.py)
and [host runner](passive-host.py) reuse the existing finite WMT/START,
provider/A53, log export and reviewed recovery paths. The [scan command](passive-scan.sh)
queries host cfg80211 state once and refuses a missing, duplicate or disabled
5200 MHz channel before interface creation. It preserves that wiphy output
privately and sends one ordinary passive scan. Its result classifier requires
a permitted channel 40 and an actual BSS block with an admitted 5 GHz frequency
before reporting this band's scan demonstration. The focused
[classification fixture](tests/userspace-result-test.py) passes absent/disabled
band, 2.4 GHz-only BSS, missing BSS and failed/incomplete transport cases without
credentials or device access.

The [guarded deployment](results/deployment-1.json) wrote logical boot2 from
the verified Gemian boot, matched the complete 16 MiB readback and confirmed
clean shutdown. It preserved the exact predecessor checksum and used the
project-wide backup; no fresh predecessor backup was made. The
[post-install preflights](results/preflight-deployed-1.json) pass against that
actual receipt. The owner selected boot2 physically and the authenticated
[runtime](results/runtime-1.json) consumed this one firmware lifetime. Channel 40
was present and permitted; one ordinary passive scan completed through iw with
a matching firmware event and returned credit. No non-event management packet
or BSS result arrived. The complete private log, wiphy output and scan output
were preserved before reviewed recovery. A53/provider regression passed.
An independent changed-boot Gemian query confirmed carrier and 5200 MHz again,
without triggering a scan. The exact candidate must not be repeated merely
because scan completion succeeded.

The missing advertised band is resolved for this test, while RF tuning and
management reception remain unproved. The next discriminating work is to
attribute receive setup/delivery, including the retained filter callbacks and
selected host initialization sequence. The [existing filter analysis](../2026-09-08-mt6797-wlan-offloads/RECEIVE.md#retained-packet-filter-handler)
leaves those callbacks unresolved; do not turn callback value bits into an
invented register write. Admit any successor operation with its exact wire
contract and finite effects before a fresh build/boot. Association and traffic
remain later verification requirements.
