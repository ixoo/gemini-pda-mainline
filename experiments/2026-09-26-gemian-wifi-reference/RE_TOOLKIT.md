# Gemian Wi-Fi reference: RE toolkit decision

This note applies to the pinned Gemian source `59e00a9144d782e148332009a835b99c43382467` and the built v2 configuration in `results/build-v2.json`. It is a source and build audit, not evidence that the v2 image booted. The current device state and v2 Wi-Fi result remain unverified.

## Use the instrumentation already present

| Capability | V2 state | Useful question | Limit |
| --- | --- | --- | --- |
| Dynamic function and function-graph ftrace | Built in; positive-controlled on v1 | Which WMT/WLAN paths ran, in what order, and for how long? | Function names and timing do not reveal arguments, return values or DMA state. |
| Kernel trace events | `CONFIG_EVENT_TRACING=y`, `CONFIG_TRACEPOINTS=y` | How did IRQ, workqueue, scheduling and power activity surround a WLAN transition? | Discover the exact event names from the running image before relying on one. Generic events do not expose vendor-private state. |
| Dynamic debug | `CONFIG_DYNAMIC_DEBUG=y` | Which existing vendor debug statements can be enabled for one bounded cycle? | Only compiled call sites and their existing fields are available; volume and sensitive output need review. |
| Symbols and DWARF | `System.map`, unstripped `vmlinux`, `CONFIG_DEBUG_INFO=y` in the checksum-covered bundle | Which source and instruction implement an observed call path or return site? | Static analysis cannot prove the branch taken on the device. Use the RE VM for binary analysis. |
| Pstore console/pmsg | Built in | What survived a failure or reset? | Preserve the old boot's evidence before recovery; a missing record is not proof a path did not run. |
| Focused vendor decision logs | Setup and stop patches | What co-clock/EMI decisions occurred, and was the firmware stop attempted, ready-cleared, bypassed or reset-requested? | V2 stop records still need a verified boot and bounded cycle. A worker wait result is not DMA-idle proof. |

The existing `trace-wmt-stop-v2.sh` is the next hardware discriminator only after the v2 boot identity and working Wi-Fi are verified. Its single-use and recovery limits still apply. The next source change should be selected from that result, not from a wish to enable every tracer. If the firmware stop reached `ready-clear` yet DMA idle is unknown, instrument the exact vendor DMA producer/consumer and IRQ-masking boundaries with bounded, typed records. If the stop was skipped or reset-requested, investigate that gate first. Keep a distinct boot candidate and decision record for each revision.

## Kprobes decision

Do **not** backport Kprobes into this 3.18 Gemian reference kernel now. The pinned arm64 Kconfig does not select `HAVE_KPROBES` or `HAVE_REGS_AND_STACK_ACCESS_API`, and its arm64 tree has no kprobe implementation. This tree's `KPROBE_EVENT` requires both `KPROBES` and register access; `KPROBES` itself requires `HAVE_KPROBES`. Thus `CONFIG_PROBE_EVENTS=n` is a consequence of missing architecture support, not a disabled diagnostic switch. Upstream arm64 selected both prerequisites by Linux 4.9, but importing that architecture code into this vendor 3.18 tree would require separate instruction, breakpoint, exception, text-patching and register-fetch review and a dedicated boot-safety validation. That cost is unjustified while the remaining Wi-Fi questions have known source locations and can be answered with small observer patches.

Reconsider Kprobes only if several independent unknown call sites remain after the focused stop/DMA observations, dynamic ftrace and existing debug sites have been exhausted. At that point, specify the exact probe locations and fields first, and treat the backport as a separate experiment rather than silently broadening the reference kernel.

## Other possible additions

- `CONFIG_TRACER_SNAPSHOT` could freeze a pre-failure ring buffer, but the current collector already captures a bounded trace and the v2 boot is not verified. Add it only for an observed overwrite or reset-loss problem.
- `CONFIG_FUNCTION_PROFILER` can count calls and durations; the existing function-graph tracer already addresses the present ordering question.
- `CONFIG_FTRACE_SYSCALLS` or userspace `strace` may help attribute an unexpected control request, but the current question is the vendor kernel's firmware-stop and DMA state.
- `CONFIG_DMA_API_DEBUG` detects API misuse; it does not prove the Mediatek DMA engine has stopped. `KGDB` requires a reliable interactive transport and can halt a live device. Neither belongs in the next reference revision without a concrete failure requiring it.
- `CONFIG_BPF=y` does not imply a usable tracing eBPF interface: the v2 config has `CONFIG_BPF_SYSCALL=n`, and dynamic kernel probe events are unavailable here. Do not plan around `bpftrace` for this image.

Keep tracing disabled by default, filter to the relevant functions/events, bound buffers and duration, record overrun state, and preserve exact kernel release, boot ID, image checksum and collector output. Prefer the existing ftrace/debugfs interfaces and source-level diagnostic patches over a new device-side RE framework.
