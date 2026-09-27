# A53 Wi-Fi core integration gate

The [A53 modern CONN provider](../2026-09-26-mt6797-modern-conn-data/A53_INTEGRATION.md)
links, while the private MT6797 WLAN transport and whole-image components have
only been compiled in a separate minimal profile. This profile selects the
same accepted A53 service and modern-provider patch foundation plus the
existing wireless proposals in canonical order. It enables the private HIF
core for a full ARM64 link. The standalone `lib/mt6797-hif-compile` adapter is
left out because the wireless tree already contains the production-side copy
of those protocol helpers.

The hypothesis is that the pinned Linux 7.1.3 tree applies the wireless
proposals cleanly and links their enabled objects alongside the modern CONN
provider. A patch conflict, Kconfig refusal or link failure must be fixed at
that exact integration boundary before adding a resource manager. The unique
evidence is the clean pushed input commit, Buildbox build/package validation,
resolved config and linked-object check. This is a source integration test,
not a replacement for the shared owner or a hardware test.

The wireless proposals have no runtime platform caller or full firmware
executor. The Gemini DTBs remain without an active modern CONN child. This
profile must not be installed on boot2; a device boot cannot answer an
ownership or Wi-Fi question until a real manager and admitted failure lifetime
are connected. The working Gemian kernel remains the hardware reference.

## First configuration result

Clean pushed commit `081c6f0ce2b6eb424b47360903efc46b7ea1e6c5` applied all
selected patches, but Buildbox stopped before compilation: the accepted
`gemini-usbdiag.fragment` requests `CONFIG_WIRELESS=n`, while the new final
fragment requested `CONFIG_WLAN=y`. The profile's final fragment now
explicitly selects `CONFIG_WIRELESS=y` as well. This is a profile-local
integration change; the accepted baseline fragment is unchanged. The failed
attempt produced no package or device candidate.

Clean pushed commit `9c7b301afd3ead91448e37089e4b6a9c938c2305`
then passed the wireless menu check, but global `COMPILE_TEST=y` enabled the
unrelated `USB_PHY` option and again failed the accepted fragment check. The
correct fix is not another configuration override: the private HIF Kconfig
requirement is now relaxed from `ARM64 && COMPILE_TEST` to `ARM64` by a
[focused patch](../../patches/proposals/0013-wifi-mediatek-allow-mt6797-hif-without-compile-test.patch).
The final fragment no longer sets global `COMPILE_TEST`. This is still a
compile-only profile; removing the restriction adds no runtime caller.

## Completed source integration

Clean pushed commit `f339e104b0989e193a3d87b8f0324a5788dd7cc6` applied
all 528 selected patches and linked the full ARM64 kernel. The fetched
Buildbox package passed its checksum inventory; the [receipt](results/build.json)
pins the inputs and package. The linked map contains the private HIF, image
plan, retained binding, EMI, remap and ordinary-transfer functions alongside
the modern CONN provider. All five Gemini DTBs are byte-identical to the
provider-only integration build, so no active CONN child was added.

The resolved configuration keeps `COMPILE_TEST=n` and enables the private HIF
core. Opening the wireless menu also turns on several unrelated drivers from
the base defconfig: 55 symbols become enabled and 91 symbols change relative
to the provider-only integration config. The compressed kernel grows from
6,057,984 to 7,112,658 bytes. A later device profile must select only the
needed Wi-Fi stack before its package is considered as a boot2 candidate.
This build exercises no resource manager, firmware execution or Wi-Fi hardware.
