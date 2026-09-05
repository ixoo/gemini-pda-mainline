#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive reviewed Git diff input, not a new format-patch author/commit claim."""
import hashlib

PATCH = 'patches/upstream-4d7d9486/0003-dt-bindings-reset-mediatek-describe-MT6797-infracfg-.patch'
PATCH_SHA256 = '88e629b8a56aa892f43949bc052322efb38ba209df7b4d5c6a8d8df936c6fb03'
HEADER = 'include/dt-bindings/reset/mt6797-resets.h'
SCHEMA = 'Documentation/devicetree/bindings/clock/mediatek,infracfg.yaml'
SCHEMA_SHA256 = '0610f891e326d1e0a7ce9ffe3ef0513ab229bf37eee8177de0999cac17157c6f'
UPSTREAM = '4d7d9486c04d917265f64c55bd23b2cc4fe7749c'


def derive(raw):
    if hashlib.sha256(raw).hexdigest() != PATCH_SHA256:
        raise ValueError('wrong complete patch 3 input')
    boundary = f'diff --git a/{HEADER} b/{HEADER}\n'.encode()
    if raw.count(boundary) != 1 or raw.count(b'diff --git ') != 2:
        raise ValueError('unexpected patch file boundaries')
    payload = boundary + raw.split(boundary)[1]
    if SCHEMA.encode() in payload or payload.count(b'diff --git ') != 1:
        raise ValueError('schema change leaked into derived input')
    return payload
