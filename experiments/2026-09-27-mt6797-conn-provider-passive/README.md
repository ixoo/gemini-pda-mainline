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

The current patch and profile are source inputs awaiting a clean Buildbox
package and candidate admission. There is no runtime result yet. Before a
device test, pin the exact package and DTB, verify the legacy provider is
disabled and that no consumer refers to the modern phandle, assemble the
accepted RAM image with the same guarded boot2 procedure, state the finite
collector and recovery budgets, and arm it before the owner selects boot2.
