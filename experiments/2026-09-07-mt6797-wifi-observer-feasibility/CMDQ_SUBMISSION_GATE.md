# Refuse CMDQ tasks in the captured headless diagnostic

The [CMDQ-off link failure](CMDQ_ISOLATION.md) established that built-in
display, power and imaging clients require the driver to link. The selected
MT6797 device tree also supplies `ap_dma_base = <0x11000000 23 0xffff0000>`.
The CMDQ record helper translates a physical address in that 64 KiB range
into subsystem 23, while the driver accepts command buffers through its
synchronous and asynchronous ioctl paths. Removing only the device-tree
property would reject helper translation but would not prove that every raw
or indirect command is excluded.

In the selected v2 implementation, both ioctl routes and the record helper
call `cmdqCoreSubmitTaskAsync()`. The wrapper alone calls
`cmdqCoreSubmitTaskAsyncImpl()`, which acquires a task, adds it to the wait
queue, and may dispatch it to hardware. A source search found no other caller
of the implementation or its static task acquisition function in the selected
tree. This supports a small, compile-time refusal before secure-path startup,
task acquisition or hardware dispatch. The
[experiment patch](patches/cmdq-submission-gate/0001-cmdq-refuse-task-submission-in-captured-diagnostic.patch)
returns `-EOPNOTSUPP`, clears a supplied output task pointer and emits one
bounded warning when the default-off captured diagnostic is selected. The
ordinary build retains the native function body. The guard covers new
software submissions through this kernel path regardless of the command
encoding, including raw buffers.

The [57-patch Buildbox link](results/cmdq-submission-gate-link.json) passed
with an exact 10-file checksum inventory, unchanged resolved configuration,
zero undefined symbols and the inherited 69 section mismatches. In the
linked ARM64 function, a non-null task output is zeroed, the first call
prints one warning, and both paths return `-95` without a call to task
acquisition. Strict Checkpatch passed with the existing CamelCase parameter
name excluded. Native compilation still uses `-w`.

This is not a runtime quiescence claim. The selected CMDQ initialization
resets its software task lists but does not by itself prove that bootloader
work is absent from GCE hardware. A boot-only diagnostic must establish that
the headless startup and USB return remain serviceable, and a later radio
admission must independently verify GCE hardware is idle before the first
Wi-Fi DMA effect. Shared clocks, CONSYS remap/protection and worker failure
lifetime also remain open. This link is not yet a boot image or a radio action.
