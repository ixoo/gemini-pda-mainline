# Retained live IRQ evidence

Sanitized excerpts from retained Gemian dmesg and `/proc/interrupts`
snippets. These are the runtime anchors for the static DT map. Counts are
point-in-time and are not reproduced here where they would be meaningless out
of context.

## GIC affinity warnings

```text
[IRQ] IRQ 101: smp affinity is not consistent with GICD_ITARGETSR
[IRQ] IRQ 102: smp affinity is not consistent with GICD_ITARGETSR
[IRQ] IRQ 103: smp affinity is not consistent with GICD_ITARGETSR
[IRQ] IRQ 354: smp affinity is not consistent with GICD_ITARGETSR
[IRQ] IRQ 355: smp affinity is not consistent with GICD_ITARGETSR
```

Linux 101-103 are SPI 69-71; 354-355 are SPI 322-323. All are cpuxgpt.

## USB and xHCI

```text
musbfsh musbfsh: USB controller ... using DMA, IRQ 105
musb-hdrc musb-hdrc: USB Peripheral mode controller ... using PIO, IRQ 159
xhci-hcd 11270000.usb3_xhci: irq 158, io mem 0x11270000
```

IRQ 105 is SPI 73 (USB11). 158/159 are SPI 126/127 (USB3/xHCI).

## EINT registrations

```text
[FUSB302]request_irq irqnum=0x183
[NVT-ts] request irq 392 succeed
Unbalanced enable for IRQ 395
genirq: Flags mismatch irq 395. ... (bmi160_accint) vs. ... (ALS-eint)
[switch] switch_irqnr=400 ... switchgpiopin=93
```

These map EINT 3 -> 387, EINT 8 -> 392, EINT 11 -> 395, EINT 16 -> 400.
EINT 395 is shared/contended between the ALS and BMI160 candidates in this
capture.

## `/proc/interrupts` snippets

```text
387:          0          0   mt-eint   3  fusb300-eint
395:          0          0   mt-eint  11  ALS-eint
```

Other retained summaries record `mt-eint 8 cap_touch`, `mt-eint 10
aw9523-eint`, `mt-eint 6` for MSDC1 card detect, `mt-eint 176` for the PMIC
external line, and `mt-eint 16 switch`.

## Non-IRQ runtime anchors

```text
msdc0.irq_lines=GICv3-111,GICv3-112
msdc1.card_detect_irq=mt-eint-6
pmic.wrapper_irq=GICv3-210
pmic.external_irq=mt-eint-176
```

The MSDC line pair reflects the two controller SPIs 79/80; the card detect is
EINT6, not an MSDC SPI.
