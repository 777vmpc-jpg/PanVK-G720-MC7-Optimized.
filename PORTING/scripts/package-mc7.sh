#!/usr/bin/env bash
set -euo pipefail

so=${1:?Expected a compiled libvulkan_panfrost.so}
reference=${2:?Expected the Faux123 release ZIP}
readelf=${3:-readelf}
mkdir -p dist
"$readelf" -h "$so" | tee dist/elf-header.txt
"$readelf" -d "$so" | tee dist/elf-dynamic.txt
"$readelf" --dyn-syms --wide "$so" > dist/elf-symbols.txt
grep -Eq 'Class: +ELF64' dist/elf-header.txt
grep -Eq 'Type: +DYN' dist/elf-header.txt
grep -Eq 'Machine: +AArch64' dist/elf-header.txt
grep -Eq '\(SONAME\).*\[libvulkan_panfrost\.so\]' dist/elf-dynamic.txt
grep -Eq 'GLOBAL +DEFAULT +[0-9]+ +HMI$' dist/elf-symbols.txt
if grep -qE 'libc\.so\.6|libstdc\+\+\.so\.6|libgcc_s\.so\.1' dist/elf-dynamic.txt; then
  exit 1
fi
python3 - "$so" "$reference" <<'PY'
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

library, reference = sys.argv[1:]
with ZipFile(reference) as release:
    meta = json.loads(release.read("meta.json"))
meta.update(
    name="PanVK G720 MC7 — port Faux123 v1.1.9",
    description="Port experimental para MT6899 com Mesa 26.3.0-devel e Kbase/CSF. "
                "Base pública e comportamento MediaTek AHB/ANB do projeto.",
    author="Mesa/Panfrost, autores dos patches Kbase/CSF e Faux123",
    packageVersion="1.1.9-mc7",
)
assert meta["libraryName"] == Path(library).name
with ZipFile("dist/PanVK-Faux123-v1.1.9-G720-MC7-ARM64.zip", "w", ZIP_DEFLATED) as out:
    out.write(library, meta["libraryName"])
    out.writestr("meta.json", json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
PY
unzip -t dist/PanVK-Faux123-v1.1.9-G720-MC7-ARM64.zip
sha256sum dist/PanVK-Faux123-v1.1.9-G720-MC7-ARM64.zip "$so" | tee dist/SHA256SUMS
