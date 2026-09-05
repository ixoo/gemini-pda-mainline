# First-baseline host readiness handoff

Host-only review at 2026-09-05 14:45 UTC, source parent
`4a000f099ed8271155ed084a641517ed0b3b6fcf`, followed by the coordinator's local
credential colocation and unchanged-tool preparation check. No device connection,
network configuration, trust enrollment, installation or observation occurred.

**Decision:** host network configuration is already saved correctly. The live
USB interface was absent. The two existing recovery credential files are now
colocated with the retained candidate and A53 keys, and local installer/tool
preparation passes. The normal custodian can use the existing tools; no further
development or build cycle is needed for these host prerequisites. Actual deployment, physical
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
  The coordinator subsequently copied both files into the A53 worker's existing
  mode-0700 credential directory using exclusive mode-0600 creation, flushing
  and readback verification. The worker independently confirmed exact existing
  source/destination bytes, ownership, regular files and mode 0600; the unchanged
  collector's private-path checks also pass. No credential bytes or fingerprints
  are recorded here.
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

1. **Offline colocation complete:** use the retained A53 worker worktree as the
   execution checkout. The coordinator checkout lacks this candidate directory
   and A53 credential directory; the worker now has all required credentials at
   the fixed paths. The original recovery files remain in the coordinator
   checkout. No candidate copy or symlink substitution is needed. Do not repeat
   the completed credential copy or treat it as a remaining setup gate.
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

## Unchanged local preparation result

The existing `scripts/install-boot2.py` ran with its three explicit retained
inputs and **without** `--execute` or `--target`: this worker's candidate
`candidate-a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf`,
the retained historical `candidate-mt6797-pwrap-reset-305230b1` foundation,
and userspace package manifest
`dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60`
from build `e9c028005b88ef8536ecb58c095e8d172253fa12`.

It exited zero with `installer_derivation=pass`, `mode=local-validation-only`,
`device_action=none` and `physical_admission=false`. This includes the unchanged
candidate/package/member/credential validation, installer derivation, Bash
syntax and ShellCheck. The generated local adapter SHA-256 was
`c3621fbc7a037708b217551ede8f6ec5d9317529084f1876e784d195dcaa5b22`;
that value binds this execution checkout's actual private paths, not a portable
deployment identity. No temporary `derive-*` directory remains.

The collector's existing source-closure check, finisher module load and private
recovery-path checks passed without calling their dispatch functions. No live
admission, deployment receipt, attempt or phase claim was created. Full collector
and phase preparation still require actual deployment/selection/prior-result
records; their absence now is an operational prerequisite, not missing software
or a reason to fabricate a dry-run admission. No device serviceability claim
follows from these local checks.
