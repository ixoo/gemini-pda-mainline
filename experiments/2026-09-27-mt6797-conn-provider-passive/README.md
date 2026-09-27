# Passive modern CONN provider on Gemini

The accepted A53 image compiles the modern MT6797 CONN domain provider but
does not describe it in the Gemini DTB. The existing SPM node instead exports
the legacy flat `mediatek,mt6797-scpsys` interface. In the exact accepted
passive-reset DTB, 24 nodes refer to that flat phandle; 23 are disabled and
the display mutex is enabled. The A53 profile disables the legacy provider.
Replacing the flat node with the modern provider would therefore strand the
existing references and confuse the single SPM register owner.

The pinned Linux 7.1.3 modern driver obtains its register map from its parent
syscon and registers only DT-described child domains. This experiment adds a
modern child under the *same* SPM syscon in a named profile, without another
`reg` range. `simple-mfd` makes the child platform device visible. The old
flat phandle and its consumers stay unchanged in this diagnostic profile;
the legacy SCPSYS driver must remain disabled. This is not a final migration
of MT6797's other power domains.

The only described modern child is CONN ID 12, with
`MTK_SCPD_KEEP_DEFAULT_OFF` and `MTK_SCPD_REQUIRE_INIT_OFF`. No device
references the modern provider. Probe must read both CONN status registers
and either register an initially OFF domain or refuse an ON, mixed or unreadable
state. It must not request a CONN power transition. This is the unique
observation for a later device boot; a successful A53 service regression
alone cannot establish provider registration.

## Decision branches

- If the child never appears, inspect `simple-mfd` population and parent
  schema/compatible matching before another boot.
- If probe refuses the initial state, preserve the exact log and SPM status.
  Do not bypass the check or cycle the island to make registration pass.
- If registration succeeds and CONN remains OFF, this clears the passive
  topology gate only. The next step is the shared owner transition with VCN,
  CONMCU reset, SPM, remap and retained-fault responsibilities.
- Any observed CONN power transition, A53 service regression or changed
  behavior of the legacy clients rejects this diagnostic candidate.

## Build and composition

Clean pushed commit `25eb161f34a61a7b15daf26f10d776e6d88b401e`
applied all 541 selected patches and built a full kernel on Buildbox. Its
immutable package inventory is `af8601b0…07c91f`; the fetched package passed
its checksum inventory. The [build receipt](results/build.json) pins the
selection. The resolved config still disables legacy `MTK_SCPSYS` and enables
the modern provider. `Image.gz` and the config are byte-identical to the
accepted passive-reset image.

The raw built Gemini DTB contains unrelated source-tree defaults, including
disabled USB and keyboard nodes, so it is not a boot2 candidate. The
[candidate builder](build-candidate.py) verified the built provider subtree,
then added only its SPM parent properties and CONN child to the boot-tested
passive-reset DTB. It compared every preexisting node and property before
packaging the unchanged kernel and RAM root. The resulting
[sanitized receipt](results/candidate.json) pins boot image
`ae6767ee…0006fd3` and full padded boot2 image `99888ffb…05c4750`.
The private image remains ignored under `artifacts/conn-provider/`.

The [deployment receipt](results/deployment.json) now confirms the live GPT
resolution of logical `boot2` to `/dev/mmcblk0p30`, the inactive/root guard,
stable external power, the exact predecessor, a synced write, full matching
readback and clean shutdown. No fresh backup was needed because the verified
project-wide backup remains in place. The first 300-second USB watcher then
expired without a mainline route or SSH claim; the device session is unconsumed.
The owner then reported selecting boot2. A second finite 300-second watcher
also saw no direct mainline USB route; bounded Gemian LAN checks were
unreachable. A later Mac USB sample found `0x0e8d:0x20ff` with product
`Unknown` and no network interface, the same intermediate identity observed
in an earlier experiment before a later successful mainline boot. No boot
identity, kernel log or provider result was obtained, so this observation
does not establish whether the installed image booted. The device session
remains unconsumed. Before another boot attempt, use the screen
state and a decision-changing diagnostic; do not repeat an identical watcher
or partition write.

For a later attended boot, [the pre-armed watcher](watch-boot.py) first checks
the exact candidate and the still-unclaimed session. Its default invocation
does only offline preparation. With `--execute`, it records local preloader,
`0x20ff` and candidate-gadget stage changes for at most 900 seconds. Only the
exact direct mainline USB route starts the existing authenticated collector;
an expired watch makes no device SSH claim. Start it before the owner selects
boot2, after the current screen state and safe shutdown are established. A
route and authenticated log would test provider registration; another stable
`0x20ff` interval would redirect boot-stage diagnosis without implying a
provider failure.

The [guarded installer](install-passive.py) pins the existing full boot2
checksum as its predecessor and the [session](passive-host.py) extends the
accepted A53 service collector with one read-only, 15-second provider probe.
It checks the live boot ID and that exactly one modern CONN platform device
is bound to `mtk-power-controller`. This probe runs after the authenticated
A53 observation and before the pre-recovery evidence seal. Its failure does
not skip log preservation or the reviewed Gemian return; it makes the provider
gate fail separately from the A53 regression.
