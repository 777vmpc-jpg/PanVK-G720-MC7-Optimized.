# Mali-G720 MC7 Android ARM64 integration

The build starts at Mesa `5a07217f034b3e50d8c7c7794f97a2df1742613b`.
`reconciled-csf.patch.gz` is the net source diff from the project's reconciled
144-patch MC7 series, including the Kbase backend and the SAME_VA / NEED_MMAP
import cleanup overlay. It contains the work-register handling previously
checked against the pristine tree by the standalone workflow.

`mc7-integration.patch` follows the reconciled series. It carries the
Optimized port's MediaTek AHB/ANB path and WSI diagnostics, the 64-bit
provoking-vertex function address fix, the placed-memory probe from the
project's `kakarot-placed-memory` branch (commit `eecb14567c5e`), and the
baseline's heap renewal defaults of 256 submissions and 262144 work units.
The CSF GPU semaphore waits remain available through
`PANVK_KBASE_GPU_SEMAPHORE_WAITS=1`.

The build uses the Android NDK r27c and the public pinned Kbase build scripts.
The official Faux123 v1.1.9 release is hash-checked and supplies the Android
package manifest schema. This port uses the common Mesa revision and the
project's recovered patches. The 49 patches from the upstream private
companion repository are unavailable. Runtime validation of BC decode,
placed memory and the BOTW Recomp swapchain requires the MT6899 device.
