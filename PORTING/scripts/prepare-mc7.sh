#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
mesa="$root/source/work/mesa"
pin=5a07217f034b3e50d8c7c7794f97a2df1742613b
patches="$root/PORTING/patches"

mkdir -p "$mesa"
git -C "$mesa" init -q
git -C "$mesa" fetch --depth=1 https://gitlab.freedesktop.org/mesa/mesa.git "$pin"
git -C "$mesa" checkout --detach FETCH_HEAD
test "$(git -C "$mesa" rev-parse HEAD)" = "$pin"
test -z "$(git -C "$mesa" status --porcelain)"

gzip -dc "$patches/reconciled-csf.patch.gz" | git -C "$mesa" apply --index -
grep -Fq 'cs_reg_count = (stream_features & 0xff) + 1' "$mesa/src/panfrost/lib/kmod/kbase_kmod.c"
grep -Fq 'MAX2(csif_info->unpreserved_cs_reg_count, 4)' "$mesa/src/panfrost/vulkan/csf/panvk_vX_gpu_queue.c"
git -C "$mesa" apply --index "$patches/mc7-integration.patch"
git -C "$mesa" diff --cached --check
