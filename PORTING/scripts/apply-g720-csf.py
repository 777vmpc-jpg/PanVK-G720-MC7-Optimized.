"""Apply the G720 fixes after the pinned public Kbase/CSF series."""
from pathlib import Path
import re
import subprocess
import sys


mesa = Path(sys.argv[1]).resolve(strict=True)
root = Path(__file__).resolve().parents[2]
fn_patch = root / "patches/0002-fix-provoking-vertex-fn-address-truncation.patch"
kbase_path = mesa / "src/panfrost/lib/kmod/kbase_kmod.c"
queue_path = mesa / "src/panfrost/vulkan/csf/panvk_vX_gpu_queue.c"

# The pinned public series already includes both changes from the G720
# register-count patch. Preserve its fallback for unexpected counts.
queue = queue_path.read_text()
job = queue.split("kbase_subqueue_emit_job(", 1)[1].split("struct cs_builder b;", 1)[0]
if not re.search(
    r"\.nr_kernel_registers\s*=\s*MAX2\(csif_info->unpreserved_cs_reg_count, 4\)", job
):
    raise SystemExit("Kbase job is missing its kernel register reservation")

kbase = kbase_path.read_text()
query = kbase.split("kbase_query_csif_info(", 1)[1].split(".scoreboard_slot_count", 1)[0]
if not (
    "cs_reg_count = (stream_features & 0xff) + 1;" in query
    and ".cs_reg_count = cs_reg_count," in query
):
    raise SystemExit("Kbase does not use the reported CSF register count")
print("Pinned Kbase/CSF series already contains both register-count fixes")

subprocess.run(["git", "-C", str(mesa), "apply", "--check", str(fn_patch)], check=True)
subprocess.run(["git", "-C", str(mesa), "apply", str(fn_patch)], check=True)
