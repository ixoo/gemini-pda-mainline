#!/usr/bin/env bash

# Audit format-patch metadata without printing author addresses or patch
# bodies. This is a review gate, not a substitute for a truthful DCO review.

set -euo pipefail
export LC_ALL=C

repo_root=${REPO_ROOT:-$(cd -- "$(dirname -- "$0")/../../.." && pwd)}
series=${SERIES:-$repo_root/patches/series}

[[ -r "$series" ]] || {
	printf 'error=missing_series:%s\n' "$series" >&2
	exit 2
}

patch_count=0
missing_from=0
placeholder_author=0
placeholder_object=0
missing_subject=0
missing_date=0
missing_signoff=0
blocker_patches=0

printf '%s\n' 'validation=patch-provenance-series'
printf 'series=%s\n' "$series"

while IFS= read -r relative || [[ -n "$relative" ]]; do
	case "$relative" in
		''|'#'*) continue ;;
	esac
	patch_count=$((patch_count + 1))
	patch="$repo_root/patches/$relative"
	[[ -r "$patch" ]] || {
		printf 'error=missing_patch:%s\n' "$patch" >&2
		exit 2
	}

	header=$(sed -n '1p' "$patch")
	from=$(sed -n 's/^From: //p' "$patch" | sed -n '1p')
	subject=$(sed -n 's/^Subject: //p' "$patch" | sed -n '1p')
	date=$(sed -n 's/^Date: //p' "$patch" | sed -n '1p')
	signoffs=$(rg -c '^Signed-off-by: ' "$patch" || true)
	signoffs=${signoffs:-0}
	object=${header#From }
	object=${object%% *}

	reasons=()
	from_state=present
	if [[ -z "$from" ]]; then
		from_state=missing
		missing_from=$((missing_from + 1))
		reasons+=(missing_from)
	elif [[ "$from" == *noreply@example.com* || "$from" == *'Gemini PDA Mainline Project'* ]]; then
		from_state=placeholder
		placeholder_author=$((placeholder_author + 1))
		reasons+=(placeholder_author)
	fi

	object_state=present
	if [[ "$object" =~ ^0{40}$ ]]; then
		object_state=placeholder
		placeholder_object=$((placeholder_object + 1))
		reasons+=(placeholder_object)
	fi

	if [[ -z "$subject" ]]; then
		missing_subject=$((missing_subject + 1))
		reasons+=(missing_subject)
	fi
	if [[ -z "$date" ]]; then
		missing_date=$((missing_date + 1))
		reasons+=(missing_date)
	fi
	if (( signoffs == 0 )); then
		missing_signoff=$((missing_signoff + 1))
		reasons+=(missing_signoff)
	fi

	if ((${#reasons[@]})); then
		blocker_patches=$((blocker_patches + 1))
		reason_text=$(IFS=,; printf '%s' "${reasons[*]}")
	else
		reason_text=none
	fi

	printf 'patch=%s from=%s object=%s subject=%s date=%s signoffs=%s reasons=%s\n' \
		"$relative" "$from_state" "$object_state" \
		"$([[ -n "$subject" ]] && printf present || printf missing)" \
		"$([[ -n "$date" ]] && printf present || printf missing)" \
		"$signoffs" "$reason_text"
done < "$series"

printf '\n[totals]\n'
printf 'patch_count=%s\n' "$patch_count"
printf 'missing_from=%s\n' "$missing_from"
printf 'placeholder_author=%s\n' "$placeholder_author"
printf 'placeholder_object=%s\n' "$placeholder_object"
printf 'missing_subject=%s\n' "$missing_subject"
printf 'missing_date=%s\n' "$missing_date"
printf 'missing_signoff=%s\n' "$missing_signoff"
printf 'blocker_patches=%s\n' "$blocker_patches"
printf 'hardware_write=none\n'

if (( blocker_patches )); then
	exit 1
fi
