#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ $# -eq 2 ]] || die "usage: build-keyboard-dtb.sh PACKAGE_DTB OUTPUT"
input=$1
output=$2
[[ -s "$input" ]] || die "package DTB is missing"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
for tool in fdtget fdtput; do command -v "$tool" >/dev/null || die "$tool is required"; done
install -m 0600 "$input" "$output"
for node in /i2c@1101c000 /i2c@1101c000/gpio-expander@5b /keyboard-matrix; do
	[[ "$(fdtget -t s "$output" "$node" status)" == disabled ]] || \
		die "expected disabled source node: $node"
	fdtput -t s "$output" "$node" status okay
	[[ "$(fdtget -t s "$output" "$node" status)" == okay ]] || die "failed to enable $node"
done
[[ "$(fdtget -t s "$output" /i2c@1101c000/gpio-expander@5b compatible)" == awinic,aw9523-pinctrl ]] || \
	die "AW9523 compatible changed"
printf 'output=%s\nsha256=%s\nenabled=/i2c@1101c000,/i2c@1101c000/gpio-expander@5b,/keyboard-matrix\n' \
	"$output" "$(sha256sum "$output" | awk '{print $1}')"
