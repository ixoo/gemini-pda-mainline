# Retained WIFI default comparison and loading applicability

The retained WIFI record differs from the retained producer's compiled default
only within the six-byte MAC-address field. Every byte outside that field
matches. This is a concrete comparison result, not evidence that the device
lacks calibration, that restoration occurred, or that default content is
unsuitable. It changes the remaining question from finding a unique calibration
file to identifying the effective calibration/configuration contract of the
exact board and firmware.

## Reconciliation and private comparison

[CALIBRATION.md](CALIBRATION.md) owns the selected 512-byte consumer layout and
version/command checks. [PROVENANCE.md](PROVENANCE.md) supersedes its unresolved
filesystem/envelope question: the retained nvdata filesystem contains the
514-byte WIFI storage file, with a matching two-byte envelope and the selected
source's version predicate. The producer family is identified; the actual
installed restoration branch remains unknown. Earlier checksum work is reused,
not repeated. No filesystem repair or installed-image checksum override was used.

This follow-up read that exact file into process memory with read-only debugfs
inside the RE VM. Both exit status and stderr were checked; the file had the
expected 514-byte extent and the existing storage inspector accepted it. The
512-byte payload was compared to `stWifiCfgDefault` in both retained ARM32 and
AArch64 `libcustom_nvram.so` files from the already attributed gemian-2019
corpus. ELF symbol extent and a containing file-backed PT_LOAD segment bounded
each read; symbol relocations also reference the default object. These are
producer-family objects, not a claim that this corpus was installed in July.

Both compiled default objects match each other. The full record does not match,
but concatenating record extents `[0,4)` and `[10,512)` matches the corresponding
compiled-default extents exactly. Hence any difference is confined to `[4,10)`,
the public layout's MAC field. This does not say that every MAC byte differs.
It covers versions, all calibration/override fields, country/regulatory fields,
flags and reserved bytes, rather than a sample or a checksum comparison.

[Sanitized comparison receipt](results/calibration-default-comparison.json).
No record/default bytes, MAC, country, RF values, private hashes, defaults,
binary listings or private filesystem paths are published. No image or record
was copied/exported, no vendor API ran, and no VM file was created. The RE shell
was closed. Prior backup/source hashes were not recomputed.

## Exact selected host branches

All source references below use Planet
`c5b0be85017ad0c599725e8273842efdbecdd88a`, gen3, with the source identities
already owned by [the calibration audit](CALIBRATION.md#exact-source-identities).
These are public branch conditions, **not a disclosure of private flag values**.

`include/config.h:746` selects `CFG_SUPPORT_NVRAM_5G=1`.
`os/linux/gl_init.c:616–624` loads the EFUSE-override region from the record and
points `prOldEfuseMapping` at it. That pointer is not an on-chip EFUSE read.
The alternative raw `CMD_ID_SET_PHY_PARAM` path in `wlan_lib.c:4154–4162` is
excluded by this selected 5GHz configuration.

| Public source condition | Host action in `common/wlan_lib.c` |
| --- | --- |
| Part-one own version 1 | At 4086–4087, force the validity variable but skip the ordinary base-power update branch. This historical-version branch does not identify the silicon. |
| Otherwise `ucTxPwrValid != 0` | At 4090–4093, call `nicUpdateTxPower` / `CMD_ID_SET_TX_PWR` with record base-power parameters. A zero flag omits that update. |
| `ucEnable5GBand != 0` | At 4118–4126, run the 5GHz parameter path before considering hardware-disable/support flags for host band enablement. |
| `r5GBandEdgePwr.uc5GBandEdgePwrUsed != 0` | At 3991–4005, submit `CMD_ID_SET_EDGE_TXPWR_LIMIT_5G`. |
| `uc5GChannelOffsetVaild != 0` | At 4011–4023, submit `CMD_ID_SET_CHANNEL_PWR_OFFSET` for 5GHz. |
| `uc11AcTxPwrValid != 0` | At 4028–4037, submit `CMD_ID_SET_80211AC_TX_PWR` for 5GHz. |
| Mapping pointer exists and `ucChannelOffsetVaild != 0` | At 4134–4150, submit `CMD_ID_SET_CHANNEL_PWR_OFFSET` for 2.4GHz. |
| `ucRssiPathCompasationUsed != 0` | At 4164–4177, submit `CMD_ID_SET_PATH_COMPASATION`. |
| `fg2G4BandEdgePwrUsed != 0` | At 4208–4221, submit `CMD_ID_SET_EDGE_TXPWR_LIMIT`. |
| Mapping pointer exists and `uc11AcTxPwrValid2G != 0` | At 4224–4236, submit `CMD_ID_SET_80211AC_TX_PWR` for 2.4GHz. |
| After these branches | At 4240–4249, submit the complete 512-byte record using `CMD_ID_SET_NVRAM_SETTINGS` (public command ID `0x48`). |

[The TX-power wrapper](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic.c#L2247)
confirms the normal command and no-response setting.

A skipped optional command leaves existing firmware state untouched by that
specific host command. It is **not** a demonstrated selection of on-chip EFUSE,
a validated fallback or proof that the final full-record command ignores that
field. The selected host routine contains no explicit command selecting the
source of on-chip calibration. The public code therefore establishes the
host override/application boundary; it does not resolve the retained firmware's
internal EFUSE/default precedence. This is the concrete remaining firmware-side
question, not a reason to infer an uncalibrated device.

The runtime NIC capability event supplies firmware/product version, hardware
5GHz-disable state and RF/BB calibration-failure fields; `wlan_lib.c:3793–3821`
records versions and logs the latter when `CFG_ENABLE_CAL_LOG=1` (selected at
`config.h:223`). Such a response has not been attributed for this exact retained
record/firmware pair by this task. MTKE container major/minor fields are not a
substitute for those capability fields. No new query is requested or performed.

The optional override and full-record submissions request no reply in this
source. That is a protocol property, not proof that loading cannot work and not
a basis for inventing a new NVRAM-applied ACK. A production implementation needs
the actual normal-command submission/resource contract and known firmware
interpretation; it must not equate queued submission with a new observed
calibration measurement. The existing frozen CONFIG/PDA/START INIT path does
not implement the normal `0x48` command protocol.

## Locally supplied record and upstream controls

The exact retained local record remains a viable configuration input candidate.
Do not substitute the compiled default, regenerate an address, transplant it to
another board, or require unique non-default RF bytes as a universal admission
condition. Equality outside MAC neither proves factory calibration nor excludes
firmware/on-chip calibration. Likewise, reconstructing the daemon's entire
restoration history is not automatically necessary to reuse a locally supplied
record once its board/firmware contract is established.

A future loading integration should bind the owner's immutable local WIFI file
to the named board, validate the already established storage envelope, retain
exactly its 512-byte payload and apply it through the exact supported firmware's
normal command path. It should keep the source/version and private ownership
context with that buffer, not derive applicability from its checksum or country.
The remaining evidence is the intended record/firmware format pairing and the
firmware-side calibration/default/EFUSE precedence, together with the actual
provider/normal-command implementation. A capability response or prior applicable
runtime evidence can corroborate that pairing when such work is admitted; this
task grants no radio action budget.

Use normal cfg80211 regulatory handling for the eventual driver: publish the
board's supported bands/channels and hardware limits, process regulatory updates
and enforce the resulting restrictions in firmware. Record country is at most
an attributed driver hint, not permission to restore the vendor's permissive
fallback tables. In particular, do not turn unchecked record subbands into a
fully trusted custom regulatory domain; that API intentionally replaces prior
channel defaults. [Upstream cfg80211 regulatory APIs](https://docs.kernel.org/driver-api/80211/cfg80211.html#regulatory-enforcement-infrastructure).
Regulatory policy and RF calibration remain distinct contracts.

No additional generic validator or speculative loading adapter is introduced:
the existing immutable record/envelope inspectors already cover host parsing,
and there is no real normal-command/provider boundary to attach a loader to.
The useful result here is the exact default-comparison evidence and the narrowed
firmware-side question. This does not impose a global radio blocker based on
absence of a distinct payload. Hardware admission and ordered implementation
work remain owned by the roadmap/coordinator.
