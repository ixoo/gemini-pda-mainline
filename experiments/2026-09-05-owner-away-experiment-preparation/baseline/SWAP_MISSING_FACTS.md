# Attended swap prerequisite — narrow missing-facts handoff

The baseline worker retains sole device custody under the coordinator's explicit
attended handoff. The currently unselected shared registry does not release that
custody. Installation was refused before staging or writing. No candidate upload,
swap change, shutdown, physical selection or Ready-for-boot2 handoff occurred.
Live access is paused. The coordinator owns shared queue changes.

The retained userspace capture inventories contain selected Android integration
services but no zram/swap startup configuration. The retained droid-hal-init
service depends on the Android LXC service; its retained shell script contains
no swap setup. This is incomplete historical coverage, not evidence that the
current system has no swap manager. No retained proprietary text is republished.

The first missing-facts prerequisite was exactly one invocation of
[`probe-swap-missing-facts.sh`](scripts/probe-swap-missing-facts.sh), via the
existing strict authenticated transport and private one-shot claim/receipt helper.
Its separately admitted one-shot execution is recorded below. Supply the privately
recorded boot identity and swap size as `EXPECTED_BOOT_ID` and
`EXPECTED_SWAP_SIZE`; no defaults or new identities are selected. Use a 30-second
transport ceiling, 65536-byte stdout and 8192-byte stderr limits, no retry.

The command confirms the recorded boot, exact one unused zram entry and the
existing memory margin before and after inspection. It reads thirteen literal
startup paths, chosen from the retained Android-container integration and common
zram startup entry points, and queries three exact service units. It performs no
recursive search. Missing, unsafe or oversized files are explicit unresolved
observations. Each regular file read is bounded to 65537 bytes; matching output is
at most 32 lines of 240 characters per file. The text digest identifies the shell
capture with trailing newlines removed, not the original file bytes. Selected
lines and service properties remain private. This is an ownership investigation,
not an immutable snapshot or automatic proof that restoration is safe.

The earlier partial receipt supplies the utility/version and backing identity
findings; do not replay the corrected full probe. A future mutation must freshly
validate those utility and device identities. A complete new receipt only closes
the command budget; its startup findings still require review. Missing referenced
imports, unresolved file types, truncated relevant context, changed state, unknown
manager behavior or timeout do not admit mutation. Do not automatically follow
new paths or expand the search.

If ownership and restoration are established, the proposed action remains one
temporary deactivation of the exact unused entry, preserving its existing format
and configuration. Abort restoration uses the same entry with reviewed original
default-priority semantics; no reset, reconfiguration or service change. The
[corrective protocol](SWAP_PREREQUISITE.md) owns mutation, rollback and uncertain
transport handling. No mutation wrapper or installer retry is admitted here.

## Attended result and corrected selector

The admitted missing-facts command completed once with exit zero, complete
framing and empty stderr. Its pre/post current-state checks passed. The private
receipt is under `artifacts/a53-authenticated/attended-install-1/` in
`swap-missing-facts-probe-1/`; no raw startup material is republished.
Its broad selection of stanza headers consumed the per-file match limit before
all potentially relevant swap lines could be emitted. Ownership therefore
remains unresolved; that is a selector limitation, not evidence that the startup
owner cannot be found. Device access paused again after the read-only result.
Custody remains held, installation remains unstarted, and no swap mutation,
shutdown or Ready-for-boot2 handoff occurred.

The next proposed command is
[`probe-swap-ownership.sh`](scripts/probe-swap-ownership.sh). It preserves the
same pre/post state gates and bounded private transport. Its exact twenty-file
scope contains the three observed rootfs startup files and seventeen literal
imports observed in the prior receipt. The rootfs ancestor directories and
selected files must not be symlinks; unsafe types, access or sizes refuse. Each
file read is bounded to 65537 bytes with a 65536-byte acceptance limit.

The selector emits every swap/zram match with its nearest preceding on/service
stanza header and every import line, without unrelated stanza bodies or per-file
match truncation. The 65536-byte total stdout ceiling still applies; overflow
makes the receipt incomplete. Imports discovered in this read are reported only;
there is no recursion, dynamic property expansion or execution. An unresolved
import must be identified precisely during result review, not silently followed.
No service action, vendor binary execution or device write is included. The
coordinator must admit the exact new source before its one-shot dispatch.

Host validation: Bash syntax and ShellCheck pass for both scripts. The corrected
ownership command has not run; no ownership resolution or runtime readiness is
claimed. These read-only selector changes need no kernel build or Buildbox access.
