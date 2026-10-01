# MT6797 regulatory configuration

The [first normal set](../2026-10-01-mt6797-first-normal-set/README.md)
completed a bounded PIO submission on hardware. This successor currently has
host validation only; it has no kernel build or device result yet.

Patches 0067–0069 register a real mac80211 wiphy with channels 1–13, 20 MHz,
legacy rates and a conservative 20 dBm driver ceiling. Effective cfg80211
channel restrictions govern the two firmware domain lists and power controls.
The pinned kernel serializes these updates with RTNL; a private mutex protects
the whole command sequence. No private country hint or custom domain is used.
Disabled, radar and no-20-MHz channels are omitted; NO_IR also enters the
passive list. More than six ranges, invalid country tags and unrepresentable
power are refusals. Negative power bytes are not channel-disable controls.

The supported record sequence is base power, optional 5 GHz edge/AC power,
passive and ordinary domains, optional 2.4 GHz edge, full immutable 512-byte
record, then CID 0x38 per-channel power. The existing record parser rejects
unsupported optional branches. Only 2.4 GHz is exposed. The private record
never supplies regulatory authority.

This differs from the newer selected host's CID 0x49 country table: private
static analysis found no 0x49 entry in the retained firmware's 81-entry mapped
normal dispatcher. That is not proof of firmware-wide absence. Supported 0x38
uses the public host's 32-byte layout: eight offsets, lower-power concurrency
policy, fourteen 2.4 GHz and four 5 GHz limits in half-dBm units. The mapped
handler copies the layout and a mapped consumer reads per-channel limits.
This is not a measurement of RF power or proof of application. The mapped
full-record handler consumes selected fields and does not itself replace those
domain lists; its called routine's effects remain separately bounded evidence.
The source contracts are in
[calibration applicability](../2026-09-05-mt6797-wifi-contract/CALIBRATION_APPLICABILITY.md)
and [normal commands](../2026-09-05-mt6797-wifi-contract/NORMAL_COMMAND.md).

After the record, only domain/power updates are admitted by the config sender.
Sequence history and finite TC4 credits persist, with no invented refill or
application ACK. Any failed configuration closes the session. Interface start,
scan, channel and packet/RF operations remain unavailable, and no automatic
station interface is created. The built-in CONSYS owner retains the successful
wiphy and powered HIF for the boot lifetime; removable-driver support remains
unfinished.

The isolated profile includes canonical 0065 followed by 0067–0069, excluding
the first-set-only caller 0066. Historical profiles are unchanged. The patches
carry a synthetic non-certifying archive author and are not submission-ready.

## Validation and next observation

The focused `tests/regulatory-test.c` uses synthetic input against actual patch
headers. It covers world/US tags, NO_IR, gaps, disabled channels, signed power,
slot/range refusal with zero output, exact record/control lengths, retained
post-record phase/credits/history, transport failure and record replay refusal.
Compile using `cc -std=c11 -Wall -Wextra -Werror -I <prepared-source>/drivers/net/wireless/mediatek/mt6797 tests/regulatory-test.c`.
It uses no physical controller. Checkpatch has zero errors and style checks;
its new-file MAINTAINERS warning remains because this experimental directory
has no upstream maintainer entry.

A future device protocol must pin the built candidate, admit one WMT/START
sequence, preserve the full private log, inspect effective wiphy channels
without creating an interface, and use reviewed recovery. Configuration
submission success would justify packet/event implementation; an error or
unexpected effect stops the candidate. Neither branch demonstrates usable
Wi-Fi, association, traffic or calibration accuracy.
