# Passive CONSYS boot candidate work item

- **Outcome:** derive and independently validate one private 16 MiB Android-v0
  boot2 candidate for the passive CONSYS observation. The candidate must use
  the exact validated Buildbox kernel package, the already reviewed
  authenticated serviceability transport, and the unchanged serviceability
  DT transform. It must admit only bounded read-only log collection of the
  exact passive record; it must never invoke the inherited TOPRGU restart path.
- **Frozen package:** repository commit
  `f9981eaf63381a558f77be251da4c2320cb4321b`; release
  `7.1.3-gemini-consys-passive`; package inventory
  `7c43a80cce28a15dc70306e3b8c225b537f1589eec4ac7411a46d422d705401c`;
  Image.gz `35ecdf4c274c222a9db2b2dc31b6b40290b7d0d563241a0b7da78cb887dba416`;
  config `7f28c03b964b7b19ed1aa383dc15fcee07e180145b3a92dd17dfda71e5927bff`;
  base DTB `d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc`.
- **Frozen private inputs:** reuse the retained TOPRGU candidate only as the
  exact authenticated initramfs/DT construction foundation, and reuse the
  validated userspace package under the ignored Buildbox export. Do not read,
  print, publish or modify private key bytes. Outputs stay mode 0700/0600 below
  `artifacts/consys-passive/` and must be Git-ignored.
- **Owned implementation scope:** Luna High owns new candidate builder,
  independent validator, collector/classifier and normal/optimized refusal
  fixtures below this experiment. It may source-pin or mechanically derive
  accepted TOPRGU candidate utilities, but must not edit the parent experiment,
  manifest, canonical series, queue, roadmap, workflow records, deployment
  installer or device evidence. `/root` owns those shared files and all device
  access.
- **Container contract:** append the unchanged serviceability DTB to the new
  Image.gz, use the reviewed AArch64 initramfs and LK Android-v0 addresses,
  produce two byte-identical assemblies, require exact source/package/config/
  DT/initramfs/input identities, exact 16 MiB zero padding and independent
  replay validation. The new release/profile must replace every parent kernel
  identity. Any retained TOPRGU wrapper must be inaccessible to the session
  collector and explicitly forbidden by the session protocol; no restart,
  reboot, poweroff, firmware, radio, MMIO, DMA or partition action is admitted.
- **Runtime record:** accept exactly one kernel-log line matching
  `mt6797-consys-passive: state=BOUND generation=<nonzero>
  client=wlan-passive power=0 reset=0 remap=0 protection=0 firmware=0 radio=0
  dma=0`. Reject missing, duplicate, malformed, `UNBOUND`, zero generation,
  unknown fields, any nonzero counter, wrong release/boot ID/architecture,
  unhealthy logger or unauthenticated transport. The collector reads bounded
  existing log bytes only, writes only private host evidence and performs no
  device-side mutation.
- **Budgets and stop conditions:** one future physical boot2 selection, one
  authenticated collection, zero automatic retries and zero automatic reboot.
  Any candidate/input/collector change invalidates readiness. Any need for a
  new DT mutation, device write, resource/effect API, firmware/radio action or
  broader session scope stops and escalates.
- **Acceptance:** host fixtures in normal and optimized Python modes; exact
  source pins; two byte-identical private candidates; independent candidate
  replay; container/DT/config/release checks; collector positive case and
  mutations for every refusal above; syntax, privacy, whitespace and repository
  gates; Sol integration review. Astra is required only if action ownership or
  hardware risk changes.
- **Handoff:** exact changed paths, command lines, hashes, case counts,
  candidate directory, candidate/input/initramfs/raw/padded identities, known
  limits and review-ready UTC. No device, deployment, commit or push action by
  the implementation owner.
- **Model route:** `gemini_implementer` (Luna High). Review returns to Sol
  Medium. `/root` remains the sole live device custodian.
- **State:** offline candidate and guarded installer packet accepted. The
  standing `boot2` installation is admitted only under every live guard;
  physical boot selection remains the owner's action.
