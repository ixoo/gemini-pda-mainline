# First-baseline host readiness handoff

Host-only review at 2026-09-05 14:45 UTC, source parent
`4a000f099ed8271155ed084a641517ed0b3b6fcf`. No device connection, network
configuration, credential copy/enrollment, installation or observation occurred.

**Decision:** host network configuration is already saved correctly. The live
USB interface is absent. The remaining offline preparation is to colocate two
existing recovery credential files with the retained candidate and A53 keys;
then the normal custodian can use the existing tools. No development or build
cycle is needed to resolve these host prerequisites. Actual deployment, physical
selection and runtime acceptance remain separate facts.

## Already complete

- macOS's saved `Gemini-L-DA921x-Bind` service maps to remembered `en7`, is in
  the current network set and is not marked inactive. Its IPv4 policy is Manual,
  `10.15.19.1`, mask `255.255.255.0`, router field `0.0.0.0`. The saved interface's
  protocol MAC matches the retained candidate's `CONFIG_CMDLINE` gadget host
  address and the historical `.82` host selector. This is saved host policy,
  not current device identity or proof that the service will reactivate.
- The reviewed [candidate and userspace](PREPARATION_RESULTS.md) remain in the
  A53 worker worktree. All six candidate member files are present, including
  `boot.img` and `boot2-padded.img`; its manifest SHA-256 is
  `54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179`.
  This inventory check does not repeat candidate validation or claim deployment.
- That worktree's `artifacts/credentials/a53-auth/` is mode 0700. The regular,
  owned mode-0600 `known_hosts` and `authorized_keys` match the candidate pins;
  its private administrator key is present with the required file metadata.
  No key material is reproduced here.
- The coordinator checkout retains owned regular mode-0600
  `artifacts/credentials/gemini_ed25519` and
  `artifacts/credentials/a53-recovery-known_hosts`. The latter matches the
  already reviewed recovery-pin handoff. No new trust was learned.
- Installer, collector, finishing helper, session generator and deployment
  receipt adapter are byte-identical between the two checkouts. Required local
  Python, Bash, ShellCheck, SSH/key tooling and reviewed shell utilities are
  available. The [session contract](SESSION.md) and
  [collector admission schema](COLLECT_BASELINE.md) already specify invocation,
  bounds, custody records and refusal behavior.

## Current host-only network evidence

`ifconfig -a` shows no live `en7`, `en8` or `en9`, no interface matching either
reviewed historical gadget host selector, and no `10.15.19.1` address. The IPv4
route table has no direct `10.15.19/24` route; the current default is on Wi-Fi
`en0`. **Do not start the one-shot SSH collector against that default route.**

The read-only `networksetup -listallhardwareports` invocation returned an
authorization error despite exit status zero. Saved policy was instead read
from the two SystemConfiguration plists, retaining only the relevant fields.
The sandbox denied `route -n get 10.15.19.82`; the route-table claim above uses
successful `netstat -rn -f inet`, not an invented successful route lookup.
Raw inventory, unrelated addresses, hardware identifiers and private host paths
are excluded from this published handoff.

Absence of a gadget interface does **not** establish an unplugged cable. It is
also compatible with a powered-off device or an OS that is not exposing this
gadget. No cable change is demonstrated necessary by this inventory. During the
coordinator's later admitted physical session, use the established direct USB
data connection; if it is already in place, no additional cable action follows
from this review. Physical boot2 selection remains the owner's action after
verified installation and the coordinator's card, never this document.

During this review the coordinator relayed another owner report that boot2 had
started, with the same host-interface absence. That report does not attribute
the running image to the new authenticated candidate. The coordinator's useful
next physical clarification is the visible screen and whether the **current**
connection is a known data-capable cable directly to the documented gadget
port, with no UART cable occupying that path. This follows the established
[physical connection prerequisite](../../2026-07-21-usb-gadget-ethernet/README.md#attended-device-and-macos-test),
not that historical experiment's probes or boot instructions. Do not request
another boot to answer it. A cable change is conditional on that clarification;
an absent interface alone cannot identify a defective cable or kernel.

## Exact remaining preparation and session handoff

1. **Offline, before installation/owner selection:** use the retained A53 worker
   worktree as the execution checkout. The coordinator checkout currently lacks
   this candidate directory and A53 credential directory; the worker lacks the
   two recovery files named above. The custodian should copy only those two
   existing files into the worker's corresponding ignored credential paths,
   with exclusive creation, mode 0600, caller ownership, no symlinks and exact
   source/destination checksum comparison. Refuse existing conflicting files.
   Retain the original recovery files. This is local reuse of existing trust,
   not host-key enrollment. Do not copy the candidate or substitute credential
   paths through symlinks. No such copy was made in this review.
2. **Use existing installation/session tooling:** recheck the exact private
   paths and current source pins in the execution checkout. Follow the existing
   installer default validation and guarded installation procedure when the
   coordinator admits deployment. Its verified receipt and actual owner
   selection supply facts that cannot be filled in now. The first collector's
   default preparation requires those real admission facts; do not fabricate
   them merely to run a dry-run before installation.
3. **After the admitted boot exposes USB:** resolve the live interface from the
   candidate's fixed gadget host selector, not remembered `en7` alone. Require
   a unique match, active carrier, unique `10.15.19.1/24` and the direct route to
   `10.15.19.82` on that same interface. The saved policy may apply automatically.
   If only the address is missing, the established host-only correction is
   `sudo ifconfig "$IFACE" alias 10.15.19.1 netmask 255.255.255.0`, with
   `IFACE` set only from that unique live match. Reinspect address and route;
   add no gateway, DNS, DHCP change or unrelated route. This command is a later
   custodian action, not executed or authorized by this scheduled review.
   If the interface is absent or ambiguous, stop; never configure another one.
4. **Run the existing first observation promptly:** use the exact
   `collect-baseline.py --admission ... --deployment-summary ... --collect`
   invocation from [COLLECT_BASELINE.md](COLLECT_BASELINE.md). Do not use a ping,
   manual SSH canary or historical open-shell collector first: those are extra
   device actions, and the historical scripts can also poll recovery or send
   commands. The current collector does not check or repair host networking;
   the custodian's local interface/route check must precede its consumed claim.
   Review its result, then use existing `finish-baseline.py` phases under
   [SESSION.md](SESSION.md), within the original logger lifetime.

Phase admission JSON files record the custodian's review of preceding evidence
and the fixed action budget. They are internal operational records, not requests
for repeated user permission. Prepare their fixed fields and command references
offline; fill result hashes and actual owner observations as they become known.
Only physical selection/availability and facts genuinely requiring the owner
remain owner interactions. A timeout never supplies a missing fact or grants a
retry. This handoff does not alter the first-boot budget or shared queue.
