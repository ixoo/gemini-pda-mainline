# Passive MT6797 CONSYS VCN supply binding

The successful [CONSYS owner boot](../2026-09-27-mt6797-consys-owner/README.md#passive-device-result)
proved the boot reservation and shared remap resource can bind. Its manager
still lacks regulator handles for the common VCN18/VCN28 rails and Wi-Fi
VCN33 rail required by the observed Gemian power sequence. This experiment
adds those three DT links and acquires their handles without changing rail
state. It does not attach a power domain, populate a child, or touch reset,
remap contents, EMI protection, firmware, radio or DMA.

The selected `mt6797-a53-consys-rails-passive` profile extends the successful
passive owner series with three separate internal format patches: the
[binding](../../patches/proposals/0024-dt-bindings-soc-require-passive-CONSYS-VCN-supply-li.patch),
[owner](../../patches/proposals/0025-soc-mediatek-acquire-passive-MT6797-CONSYS-VCN-handl.patch),
and [Gemini DT](../../patches/proposals/0026-arm64-dts-mediatek-link-Gemini-CONSYS-VCN-supplies.patch).
The patches use a synthetic, non-certifying author and have no DCO sign-off.
The original passive profile and candidate remain frozen.

## Build and device decision

Compile hypothesis: the pinned Linux 7.1.3 kernel links the owner with
`devm_regulator_get_optional()` for all three named supplies, and the Gemini DTB
resolves them to MT6351 regulator nodes without adding a CONN consumer or
regulator enable policy. A patch, config, schema, compile or DT error refuses
candidate assembly. Build only from a clean pushed commit with
`KERNEL_PROFILE=mt6797-a53-consys-rails-passive ./scripts/build-kernel --backend buildbox`.

The optional-get API is intentional: the ordinary get API can substitute a
dummy supply when constraints are complete. Missing real providers must defer
or fail this gate, never produce a false success record.

Device hypothesis, conditional on a validated package and exact boot2 image:
the owner binds all three *real provider handles* in one authenticated
mainline boot while the A53 service baseline remains healthy. The unique
observation is a changed-boot complete kernel log with one exact owner
success record and no regulator dummy, deferred, or failed probe, joined to
the DTB's three phandles and the selected build/package identities. An owner
probe failure redirects DT/provider diagnosis; a boot or service regression
stops this candidate and invokes the reviewed recovery path after preserving
evidence. One successful boot consumes this passive gate; repeating it would
not establish rail sequencing or usable Wi-Fi.

Use the reviewed live-GPT boot2 guard, exact predecessor/full readback and
clean shutdown for installation. The owner selects boot2 physically. Collect
through authenticated mainline USB, preserve a complete log and service
result, then use only the reviewed identity-gated return to changed-boot
Gemian. The standing device authorization covers this bounded test. No radio,
regulator enable/disable, power-domain transition, reset, remap write,
protection call or firmware load is admitted by this candidate.

Successful acquisition proves provider linkage and handle lifetime only. It
does not prove voltage, electrical rail state, exclusive votes, safe ordering,
external-writer exclusion, or an EMI policy. The next effect-bearing owner
slice still needs those contracts and a retained failure path before child
attachment or firmware execution.
