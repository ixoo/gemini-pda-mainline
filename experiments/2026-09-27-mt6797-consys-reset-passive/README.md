# Passive CONMCU reset binding for the shared Wi-Fi owner

The permanent MT6797 CONSYS owner already binds the boot reservation, shared
remap register and three real VCN regulator handles. It still has no handle to
the independent CONMCU reset line needed to hold the controller through a
future ordered power transition. The selected TOPRGU driver already exposes
that line as `MT6797_TOPRGU_CONMCU_SW_RST` (bit 12); duplicating its keyed
register writer in the Wi-Fi driver would create a second reset authority.

The [single internal format patch](../../patches/proposals/0028-soc-mediatek-bind-MT6797-CONMCU-reset-to-owner.patch)
requires one named reset phandle, links Gemini's existing TOPRGU provider and
acquires a nonoptional exclusive reset handle during owner probe. It adds no
`reset_control_assert()` or `reset_control_deassert()` call, regulator vote,
CONN domain attachment, remap write, EMI change, firmware load or WLAN child.
The owner remains built in and suppresses manual unbinding. The patch was
exported from three exact files in the previously prepared Buildbox A53
firmware-prepare source, with SHA-256 inputs `c6750fa7…4deb4c2`,
`2fa60456…e72b4976` and `44aa0d05…6bd315` for the binding, owner and
Gemini DTS respectively. Its synthetic author does not certify DCO.

The `mt6797-a53-consys-reset-passive` profile extends the validated
firmware-prepare series in canonical order and retains its exact A53 config
fragments. Its compile hypothesis is that Linux 7.1.3 applies the patch,
resolves the reset and watchdog providers, links the owner and produces a
Gemini DTB with exactly one CONMCU reset phandle on the owner. A patch,
schema, config, compilation, DTB or package failure refuses promotion. Build
only from a clean pushed commit:

```sh
KERNEL_PROFILE=mt6797-a53-consys-reset-passive ./scripts/build-kernel --backend buildbox
```

A successful build is not a boot candidate or proof that the reset provider
registered on the PDA. The next bounded passive device gate would require a
guarded boot2 candidate and one authenticated changed boot. Its unique
observation is owner probe success with all existing resources plus the
exclusive CONMCU reset handle, a complete log and changed-boot Gemian return.
Probe refusal redirects the provider/phandle investigation; successful binding
allows the later owner transition to use the real reset API. Neither result
admits a reset assertion, rail transition, EMI write or firmware execution.
