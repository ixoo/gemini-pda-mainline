# Live Gemian Wi-Fi NVRAM identity

This experiment prepares one bounded read-only session to decide whether the
running Gemian Android container exposes the selected Wi-Fi consumer path and
whether its 514-byte WIFI envelope, `nvram_daemon`, and selected `libnvram.so`
match already audited retained inputs. It closes only live filesystem and
installed-implementation identity. It cannot identify the restoration branch,
factory provenance, board/RF applicability, firmware application, regulatory
safety or transmit authorization.

The public contract is in [SESSION.md](SESSION.md). The fixed-path streamed
collector is [remote-collect.sh](remote-collect.sh); [collect.py](collect.py)
embeds that reviewed script in the single SSH command and enforces the host
deadline, output cap, private admission, digest confinement, ACK barrier,
sanitization and one-attempt rule. SSH uses only the exact pinned
`artifacts/credentials/a53-recovery-known_hosts` file and disables ambient
OpenSSH configuration. The default invocation is deliberately a
dry run:

```sh
python3 experiments/2026-09-06-mt6797-wifi-live-nvram-identity/collect.py
```

Run the hardware-free refusal fixtures with:

```sh
python3 -B experiments/2026-09-06-mt6797-wifi-live-nvram-identity/test_collect.py
```

The private admission is not present in this repository. It must be assembled
by the integration owner from the retained verified record, daemon and library
inputs and the expected current boot identity. No device, private capture,
network, VM, kernel build or staging access was performed for this preparation.

After independent acceptance, the integration custodian assembled the ignored
private admission from retained inputs and made one live attempt. It stopped
before the ACK barrier with an identity-or-authenticated-SSH refusal. No
mount/file read was admitted, no attempt marker was consumed and no retry was
made. See the
[sanitized pre-admission refusal](results/pre-admission-refusal-20260906.md).
The packet is not currently ready for another live invocation: first establish
the live known-good OS and transport, and review a fresh admission if its boot
identity changed.

Even a narrow pass is only attributable byte identity at the observed paths;
it is not a calibration, firmware, RF or hardware-support claim. The exact
source contract and its limitations are recorded in the preceding
[WIFI contract](../2026-09-05-mt6797-wifi-contract/PROVENANCE.md).
