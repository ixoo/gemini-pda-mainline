# Exact harmless disconnect-proof protocol

## Hypothesis and scope

On the exact authenticated baseline candidate, losing one no-PTY Dropbear
client while the separately built harmless probe child is live causes the
monitor and child to become terminal and reaped within the scaled 500 ms
lifecycle bound. Their four bounded files remain in RAM, and one independent
reconnect can export them after a complete process/descriptor scan establishes
that no monitor, observer, tty1 or input reader survives.

This proof opens no evdev node or VT and produces no keyboard result. It uses
the fixture-only child already frozen in enabled package
`0baad6b85ae68770b783245e2f1dcd7eeb4ef40d93c19e0b30e1f89f8adc3065`:

- monitor SHA-256 `4363a7d61d818bc443d5cfd76455ac38fc2cea35178d44a2dc81c229ff97b67f`;
- harmless probe SHA-256 `560d00ab80040b90fead5d0a5b2672ed633f62599aa483ff0a33be0fa74d3681`,
  66,760 bytes;
- source revision `93e2b8526daa683c2ba848011fac757a398a13dd`.

The kernel/DT/config hypothesis remains the unchanged raw candidate
`a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf`
with candidate-manifest SHA-256
`54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179`.
This protocol does not rebuild or replace it.

## Admission and exact effects

[`disconnect.py`](../2026-09-05-owner-away-experiment-preparation/keyboard/disconnect.py)
accepts a proof-specific admission rather than a future capture receipt. Before
any claim or packet, it reparses the complete authenticated baseline/recovery
archive, exact candidate and credentials, enabled package inventory, current
source closure, fresh mainline boot ID and six affirmative custody facts. The
local USB interface and direct route must also pass the existing read-only host
gate. Missing retained baseline bytes refuse before device contact.

After those checks, the fixed effect budget is:

1. Create one local claim for exactly one probe connection, one independent
   export connection and zero retries.
2. In the first no-PTY connection, recheck boot/release/initramfs, Dropbear and
   administrator-shell identities plus RAM-only paths. Create the once-only
   `/a53-keyboard-disconnect` tree, deliver only the 66,760-byte probe, and run
   it against its dedicated `run` child directory in the fixture's explicit
   `ignore` mode. That child ignores TERM, so cleanup is either a direct
   process-group HUP or the monitor's bounded TERM/KILL branch; a TERM-terminal
   child is not a possible accepted outcome for this selected mode.
3. After the exact `fixture-child=<pid>` marker is received and all command
   bytes have entered the SSH client, kill that local SSH process group with
   `SIGKILL`. The measured marker-to-kill interval must be at most 100 ms. A
   missing, extra or late marker refuses. An early marker, incomplete stdin or
   over-limit diagnostic is retained as a non-pass rather than raising inside
   the runner, allowing the separately bounded export to preserve remote
   partial evidence.
4. In one new no-PTY connection, wait at most two seconds for the retained outer
   exit, require value 2, then scan at most 512 processes and 4,096 descriptors.
   Any inaccessible inventory item, surviving deployed probe or observer
   command/executable (including a deleted executable), tty0, tty1, console or
   input descriptor refuses. Both the monitor and its forked child retain the
   deployed probe executable identity and are therefore covered. Export the
   exact four retained files with per-member limits. Remote evidence is never
   removed.
5. Reparse the export locally and run the semantic prerequisite verifier over
   all seven fixed mode-0600 evidence files before writing a passing receipt.

The host execution gate remains default-off in this review revision. Enabling
it is a separate frozen edit after specialist acceptance and recovery of the
exact private baseline archive.

## Decision branches

- **Pass:** marker-to-kill is at most 100 ms; the monitor reports cancelled or
  forward-close cleanup, terminal/reaped child, permitted signal/timing/order,
  no late state and exact byte counts; outer exit is 2; export is complete; and
  the reader scan is empty. The receipt may populate only the same boot's later
  capture admission.
- **Fail:** retained evidence proves a contradictory, late, nonterminal,
  non-reaped or surviving-reader result. Stop the keyboard session and recover;
  no retry and no keyboard claim.
- **Inconclusive:** either connection, export, inventory or framing is
  incomplete. Preserve every available local and remote partial, stop, and
  recover; absence of evidence never becomes a pass.

Every branch leaves physical boot selection and recovery with the owner. No
automatic reboot, shutdown, storage access, keyboard read or reader process is
part of this proof.

## Current stop

The reviewed private baseline archive formerly held in the A53 execution
worktree is not present in any current worktree, the primary project's ignored
artifact tree, temporary storage or Buildbox. The enabled monitor package and
current A53 credentials are retained, but `completed_baseline()` correctly
requires the original `attempts/2a40562a-7ee3-4899-af82-b0faa19df575` and
matching recovery-session bytes. Those exact runtime bytes cannot be recreated
from published summaries. Therefore no proof admission can yet be constructed,
and the device must not be contacted through this protocol until the archive is
recovered or a separately reviewed fresh baseline/recovery chain is performed.

A bounded strict-host-key LAN check at `2026-09-07T22:14:15Z` established that
the named device is reachable in known-good Gemian release `3.18.41+` with boot
ID `2b2a317f-94ff-43b3-a51f-2fa6c5ba0bf9`. The final root-source subcommand was
rejected by a quoting error and was not retried; it is not needed for the OS
identity conclusion. This observation does not select boot2 or repair the
missing private baseline archive.

One separately bounded read-only live-GPT preflight then resolved logical
`boot2` as inactive, unmounted `/dev/mmcblk0p30`, confirmed its exact 16 MiB
size, no holders, stable external power and unchanged Gemian boot ID, and read
its full-partition checksum once. The result is
`08fc061475b4bd6bc274bef6cb61c6e0a1cb8d786c5be197b79dba006bebb1c2`,
the retained consys-passive candidate—not the required baseline padded checksum
`a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821`.
No partition write or power action occurred. Therefore the keyboard candidate
must be reconstructed and byte-validated before the standing guarded boot2
installation can be used; the existing partition must not be relabelled or
treated as that candidate.

## Host validation in this revision

Six disconnect tests cover deliberate process-group loss, early-marker refusal,
complete export
framing, semantic receipt acceptance and contradictory lifecycle refusal,
absence of evdev/VT paths from the first command, and default-off ordering.
The six prerequisite tests add a rehashed 101 ms transport refusal; the six
capture tests still pass. Python compilation and whitespace checks pass. No
device, network, Buildbox or kernel action was performed.
