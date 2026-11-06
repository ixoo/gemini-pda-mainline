#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
#
# F5b: read-only snapshot of the FM audio path while fm-listen runs.
# Prints the AFE registers of the CONSYS I2S input, its ASRC (with the
# frequency calibrator's results), the routes and the ADDA downlink, then every
# DAPM widget of the card that is powered. Reads debugfs only; writes nothing.

set -u
regs=
for d in /sys/kernel/debug/regmap/*audio-controller*; do
    [ -d "$d" ] && regs=$d && break
done
if [ -z "$regs" ] || [ ! -r "$regs/registers" ]; then
    echo "no AFE regmap in debugfs"
    exit 1
fi
echo "regmap: ${regs##*/}"
# AUDIO_TOP_CON0/1, AFE_DAC_CON0/1, AFE_I2S_CON, AFE_CONN3/4, AFE_I2S_CON1,
# ADDA DL SRC and UL/DL, AFE_CONN13/14, AFE_ASRC_CON0-21.
want='0000 0004 0010 0014 0018 002c 0030 0034 0108 010c 0120 0124 0450 0454
0500 0504 0508 050c 0510 0514 0518 051c 0520 0524 0528 052c
0550 0554 0558 055c 0560 0564 0568 056c 0570'
# The file's offsets are as wide as the largest register, so compare values.
while IFS=: read -r off val; do
    case "$off" in
    *[!0-9a-fA-F]*|'') continue ;;
    esac
    for w in $want; do
        if [ "$((0x$off))" -eq "$((0x$w))" ]; then
            echo "$w:$val"
        fi
    done
done < "$regs/registers"

card=/sys/kernel/debug/asoc/mt6797-mt6351
if [ -d "$card" ]; then
    echo "powered widgets:"
    for f in "$card"/*/dapm/* "$card"/dapm/*; do
        [ -f "$f" ] || continue
        line=$(head -1 "$f" 2>/dev/null)
        case "$line" in
        *": On "*|*": On") echo "  $line" ;;
        esac
    done
    for w in "Connsys I2S" "I2S_IN_CLK" "Hostless FM DL" "Hostless FM UL" \
        "ADDA_DL_CH1" "ADDA_DL_CH2" "ADDA Playback"; do
        f=
        for g in "$card"/*/dapm/"$w"; do
            [ -f "$g" ] && f=$g && break
        done
        if [ -n "$f" ]; then
            echo "-- $w"
            cat "$f"
        else
            echo "-- $w: no widget"
        fi
    done
else
    echo "no card in asoc debugfs"
fi
