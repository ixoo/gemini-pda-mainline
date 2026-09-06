# Work item: live Gemian Wi-Fi NVRAM identity session

- **Outcome:** prepare one bounded, read-only session that decides whether the
  currently running known-good Gemian/Android environment presents the exact
  selected Wi-Fi consumer path, whether its 514-byte WIFI storage record is
  envelope-valid and byte-identical to the retained verified `nvdata` record,
  and whether the installed `nvram_daemon` plus `libnvram.so` are byte-identical
  to the already audited retained producer-family inputs. This can close live
  filesystem and installed-implementation identity only; it cannot establish
  which restoration branch ran, factory provenance, board/RF applicability,
  firmware application, regulatory safety or transmit authorization.
- **Owner and reviewer:** Luna High owns only this experiment's session tooling;
  `/root` integrates and is the sole device custodian; Sol Medium reviews the
  frozen packet and result. The implementer is not alone in the worktree and
  must preserve all concurrent edits.
- **Scope:** add README, SESSION, a host runner, one streamed read-only remote
  collector, synthetic/refusal tests and an offline validation receipt below
  this experiment only. Do not edit shared queue/roadmap/hardware/workflow files,
  existing Wi-Fi experiments, manifests, series or kernel inputs. Do not access
  the device or private captures. The integration owner separately creates a
  mode-0600 ignored admission containing the expected public release,
  architecture and boot ID plus three private SHA-256 comparison values. The
  public identities may appear in sanitized output; the private hashes may not.
- **Frozen parent and inputs:** repository commit
  `5b879ccb941a5853b70f1f7744da169be76b18f7`; selected public consumer/storage
  contract in `experiments/2026-09-05-mt6797-wifi-contract/CALIBRATION.md` and
  `PROVENANCE.md`; current recovery observation is Gemian `3.18.41+`, AArch64,
  boot ID `c8e2c5cb-ab22-4c2f-b5ab-51c1e0ee5831`. The runner must take the
  expected boot ID from a private mode-0600 admission rather than silently
  accepting a newer boot.
- **Fixed live paths:** obtain the running Android container's single init PID
  through `lxc-info -n android -sH -pH`; require state RUNNING and one numeric
  PID. From that PID's namespace view inspect only `/proc/PID/mountinfo`,
  `/proc/PID/root/data/nvram/APCFG/APRDEB/WIFI`,
  `/proc/PID/root/vendor/bin/nvram_daemon`, and the one ABI path selected by a
  fixed `/proc/PID/root/vendor/lib/libnvram.so` path. The audited daemon is
  ARM32, so the separately present AArch64 library is not an alternative
  runtime dependency for this identity check. Do not enumerate directories,
  processes, partitions or arbitrary paths. Read at most 256 KiB plus one
  oversize-detection byte, parse mountinfo only when the input is no larger
  than 256 KiB, and retain only exact `/nvdata` and `/data/nvram` relations;
  never emit unrelated mount text.
- **Private data boundary:** the remote side may read/hash exactly the three
  fixed regular files and may inspect all 514 WIFI bytes solely to check the
  already documented `0xaa` plus alternating-add/XOR trailer. It must emit raw
  digests only into a mode-0700 ignored attempt directory captured by the host,
  never to the terminal or Git. The host compares them with the private
  admission and emits a sanitized record containing booleans/counts only. No
  MAC, country, calibration value, file bytes, raw digest, mount source,
  identifier, arbitrary path or exception text may enter sanitized output.
- **Finite protocol:** default is dry-run and performs no SSH. Execute mode owns
  one strict pinned-host authenticated SSH process, one streamed script, a
  15-second remote deadline, 20-second host deadline and 8 KiB combined-output
  cap. Check release, architecture and boot ID before any container query and
  again after all reads. After stable initial identity and one RUNNING numeric
  container PID are established, durably mark the attempt consumed immediately
  before the first mount/file read. PID/state failure before that marker is a
  refusal that consumes no read; every failure after the marker is consumed.
  Require regular non-symlink files, exact WIFI size 514, daemon/library size
  caps of 4 MiB each, and at most 256 KiB of parsed mountinfo input plus one
  oversize-detection byte. No remote temporary file. Failure after identity
  admission consumes the single read;
  no automatic retry.
- **Excluded effects:** no sudo, mount, namespace entry, `lxc-attach`, service
  action, radio/rfkill/network change, firmware load, ioctl, debugfs, device
  node, MMIO, sysfs write, partition access, reboot, boot2 selection, thermal
  sampling or log dump. Existing networking may remain active; this packet does
  not claim RF silence.
- **Result branches:** exact stable identity, mount relation, three digest
  matches, 514-byte size and envelope check is a narrow pass. Missing/multiple
  container identity before the durable marker is refusal; inaccessible fixed
  input, mount ambiguity, digest or envelope mismatch after it is a
  negative/inconclusive result to preserve, not a reason to weaken checks.
  Initial kernel/boot/host/auth mismatch also consumes no read. Every failure
  after the durable marker consumes the attempt. Non-root access to the
  root-owned container PID's mount/root views is the principal live feasibility
  risk; an access refusal is an honest consumed inconclusive result. No
  result authorizes radio initialization or a mainline candidate.
- **Validation:** tests must prove default no-SSH behavior; exact command/path
  allowlist; strict key/host options; mode checks for key/admission/output;
  timeout/output caps; identity drift; symlink/nonregular/oversize fixed files;
  malformed mountinfo; every WIFI truncation/extension and bad
  trailer; raw-output confinement; digest mismatch; sanitized schema/privacy;
  attempt non-overwrite and consumed-state refusal. Run tests normally and with
  Python optimization if Python is used, `bash -n` and ShellCheck for shell,
  JSON parsing, link/privacy/source-rights scans, `git diff --check` and the
  common repository gate. Linux-only checks may be documented, never promoted.
- **Hardware:** implementation performs none. After independent acceptance, the
  integration owner may create the private admission from already retained
  inputs and execute this exact one-read packet while the observed Gemian boot
  remains current. No physical owner action is required. A changed boot
  invalidates readiness and requires a newly reviewed admission; it does not
  authorize an automatic repeat.
- **Upstream:** evidence-only prerequisite for a later standard wireless driver
  and shared CONSYS owner. No vendor code, firmware/calibration redistribution,
  DCO certification, kernel patch or support claim.
- **Handoff:** exact paths/digests of public tooling, complete command/effect
  allowlist, tests/refusals, validation output, private-input placeholders,
  known limits and explicit confirmation of no device/private access.
- **State:** offline implementation and independent review accepted; the first
  live invocation refused before admission and consumed no read. No automatic
  retry is authorized; live OS/transport must be re-established and any changed
  boot requires a newly reviewed admission.
- **Efficiency loop:** if accepted as an offline item, record one sanitized
  measurement under the active workflow cohort; the later device run is not an
  offline item.
