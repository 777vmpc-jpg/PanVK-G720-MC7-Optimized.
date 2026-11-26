#!/usr/bin/env python3
"""Port the Faux123 1.1.9 MediaTek linear-AHB usage behavior to pinned Mesa source.

This is a behavior-level source reconstruction from the recovered 1.1.9 ELF and
the MT6899 display report; Faux123's 49 private source patches are unavailable.
"""
from pathlib import Path

ROOT = Path("source/work/mesa")

def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    data = p.read_text()
    if new.strip() in data:
        return
    count = data.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}: expected exactly one anchor, found {count}: {old[:120]!r}"
        )
    p.write_text(data.replace(old, new, 1))

def replace_in_function(path: str, function_name: str, old: str, new: str) -> None:
    p = ROOT / path
    data = p.read_text()
    start = data.find(function_name)
    if start < 0:
        raise SystemExit(f"{path}: function not found: {function_name}")
    end = data.find("\n}\n", start)
    if end < 0:
        raise SystemExit(f"{path}: end of function not found: {function_name}")
    body = data[start:end]
    if new.strip() in body:
        return
    count = body.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}:{function_name}: expected one anchor, found {count}: {old!r}"
        )
    body = body.replace(old, new, 1)
    p.write_text(data[:start] + body + data[end:])

vk_android_c = "src/vulkan/runtime/vk_android.c"
vk_android_h = "src/vulkan/runtime/vk_android.h"
physical = "src/panfrost/vulkan/panvk_physical_device.c"

# os_get_option() is Mesa's Android-safe option reader. The system property
# identifies MediaTek platforms such as this phone's MT6899.
replace_once(vk_android_c,
    '#include "util/os_file.h"\n',
    '#include "util/os_file.h"\n#include "util/os_misc.h"\n')
replace_once(vk_android_c,
    '#include <unistd.h>\n',
    '#include <unistd.h>\n#include <string.h>\n'
    '#ifdef __ANDROID__\n#include <sys/system_properties.h>\n#endif\n')

helpers = """static struct u_gralloc *_gralloc;

/* Faux123 1.1.9 behavior: request CPU-usable AHB metadata and, on MediaTek
 * Kbase devices, prefer a linear-compatible gralloc allocation. */
static bool vk_android_cpu_usable_swapchain_requested;
static bool vk_android_linear_swapchain_requested;

void
vk_android_request_cpu_usable_swapchain_buffers(void)
{
   vk_android_cpu_usable_swapchain_requested = true;
}

void
vk_android_request_linear_swapchain_buffers_on_mediatek(void)
{
#ifdef __ANDROID__
   char platform[PROP_VALUE_MAX] = {0};
   if (__system_property_get("ro.board.platform", platform) >= 2 &&
       platform[0] == 'm' && platform[1] == 't')
      vk_android_linear_swapchain_requested = true;
#endif
}

static bool
vk_android_swapchain_cpu_usage(VkFormat format, VkImageUsageFlags usage)
{
   (void)format;
   (void)usage;

   if (!vk_android_cpu_usable_swapchain_requested)
      return false;

   const char *option = os_get_option("PANVK_ANB_LINEAR");
   if (option && option[0] && strcmp(option, "0") != 0)
      return true;

   return vk_android_linear_swapchain_requested;
}
"""
replace_once(vk_android_c,
    'static struct u_gralloc *_gralloc;\n',
    helpers)

anb_old = """   return vk_gralloc_to_drm_explicit_layout(&gr_handle, out,
                                            out_layouts, max_planes);
}"""
anb_new = """   VkResult result = vk_gralloc_to_drm_explicit_layout(&gr_handle, out,
                                                        out_layouts, max_planes);
   if (result != VK_SUCCESS ||
       out->drmFormatModifier != DRM_FORMAT_MOD_INVALID)
      return result;

   const char *no_linear_fix = os_get_option("PANVK_ANB_NO_LINEAR_FIX");
   const uint64_t cpu_usage =
      AHARDWAREBUFFER_USAGE_CPU_READ_RARELY |
      AHARDWAREBUFFER_USAGE_CPU_WRITE_RARELY;

   /* Only override an unknown layout for the exact fallback-gralloc case
    * demonstrated by the MT6899 report: RGBA8888 color target, CPU-usable
    * swapchain buffer, and a linear request from the MediaTek rule. */
   if (!vk_android_cpu_usable_swapchain_requested ||
       !vk_android_swapchain_cpu_usage(pCreateInfo->format, pCreateInfo->usage) ||
       no_linear_fix ||
       pCreateInfo->format != VK_FORMAT_R8G8B8A8_UNORM ||
       native_buffer->format != HAL_PIXEL_FORMAT_RGBA_8888 ||
       !(pCreateInfo->usage & VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT) ||
       (((uint64_t)native_buffer->usage & cpu_usage) != cpu_usage) ||
       pCreateInfo->extent.depth != 1 || pCreateInfo->arrayLayers != 1 ||
       native_buffer->stride <= 0 ||
       (uint32_t)native_buffer->stride < pCreateInfo->extent.width ||
       max_planes < 1)
      return result;

   const uint64_t row_pitch = (uint64_t)native_buffer->stride * 4;
   if (pCreateInfo->extent.height &&
       row_pitch > UINT64_MAX / pCreateInfo->extent.height)
      return result;

   const uint64_t size = row_pitch * pCreateInfo->extent.height;
   out->drmFormatModifier = DRM_FORMAT_MOD_LINEAR;
   out->drmFormatModifierPlaneCount = 1;
   out->pPlaneLayouts = out_layouts;
   out_layouts[0] = (VkSubresourceLayout) {
      .offset = 0,
      .size = size,
      .rowPitch = row_pitch,
      .arrayPitch = size,
      .depthPitch = size,
   };

   mesa_logi("[swapchain] swapchain buffer %ux%u vkformat %u hal %d stride %d usage 0x%llx gralloc fallback linear-forced 1 -> result 0 modifier 0x0 plane0 offset 0 pitch %llu",
             pCreateInfo->extent.width, pCreateInfo->extent.height,
             pCreateInfo->format, native_buffer->format,
             native_buffer->stride, (unsigned long long)native_buffer->usage,
             (unsigned long long)row_pitch);

   return VK_SUCCESS;
}"""
replace_in_function(vk_android_c, "vk_android_get_anb_layout(", anb_old, anb_new)

usage2_old = """   /* for front buffer rendering */
   if (swapchainImageUsage & VK_SWAPCHAIN_IMAGE_USAGE_SHARED_BIT_ANDROID)
      *grallocProducerUsage |= vk_android_get_front_buffer_usage();

   return VK_SUCCESS;
"""
usage2_new = """   /* for front buffer rendering */
   if (swapchainImageUsage & VK_SWAPCHAIN_IMAGE_USAGE_SHARED_BIT_ANDROID)
      *grallocProducerUsage |= vk_android_get_front_buffer_usage();

   if (vk_android_swapchain_cpu_usage(format, imageUsage)) {
      *grallocConsumerUsage |= AHARDWAREBUFFER_USAGE_CPU_READ_RARELY;
      *grallocProducerUsage |= AHARDWAREBUFFER_USAGE_CPU_WRITE_RARELY;
   }

   return VK_SUCCESS;
"""
replace_once(vk_android_c, usage2_old, usage2_new)

ahb_old = """   const uint64_t ahb_usage = vk_image_format_info_to_ahb_usage(info);
   if (!vk_ahb_probe_format(ahb_format, ahb_usage)) {"""
ahb_new = """   uint64_t ahb_usage = vk_image_format_info_to_ahb_usage(info);
   const bool force_linear =
      vk_android_swapchain_cpu_usage(info->format, info->usage);
   if (force_linear) {
      ahb_usage |= AHARDWAREBUFFER_USAGE_CPU_READ_RARELY |
                   AHARDWAREBUFFER_USAGE_CPU_WRITE_RARELY;
   }

   mesa_logi("[swapchain] AHB usage query: vkformat %u usage 0x%x -> AHB usage 0x%llx (cpu %d, force-linear %d, linear rule %d)",
             info->format, info->usage, (unsigned long long)ahb_usage,
             force_linear ? 1 : 0, force_linear ? 1 : 0,
             vk_android_linear_swapchain_requested ? 1 : 0);

   if (!vk_ahb_probe_format(ahb_format, ahb_usage)) {"""
replace_once(vk_android_c, ahb_old, ahb_new)

replace_once(vk_android_h,
    'struct u_gralloc *vk_android_get_ugralloc(void);\n',
    'struct u_gralloc *vk_android_get_ugralloc(void);\n'
    'void vk_android_request_cpu_usable_swapchain_buffers(void);\n'
    'void vk_android_request_linear_swapchain_buffers_on_mediatek(void);\n')

stub_old = """static inline struct u_gralloc *
vk_android_get_ugralloc(void)
{
   return NULL;
}
"""
stub_new = """static inline struct u_gralloc *
vk_android_get_ugralloc(void)
{
   return NULL;
}

static inline void
vk_android_request_cpu_usable_swapchain_buffers(void)
{
}

static inline void
vk_android_request_linear_swapchain_buffers_on_mediatek(void)
{
}
"""
replace_once(vk_android_h, stub_old, stub_new)

def replace_in_function(path: str, function_name: str, old: str, new: str) -> None:
    p = ROOT / path
    data = p.read_text()
    start = data.find(function_name)
    if start < 0:
        raise SystemExit(f"{path}: function not found: {function_name}")
    end = data.find("\n}\n", start)
    if end < 0:
        raise SystemExit(f"{path}: end of function not found: {function_name}")
    body = data[start:end]
    if new.strip() in body:
        return
    count = body.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}:{function_name}: expected one anchor, found {count}: {old!r}"
        )
    body = body.replace(old, new, 1)
    p.write_text(data[:start] + body + data[end:])

replace_in_function(
    physical,
    "panvk_physical_device_init_kbase(",
    '   unsigned arch = pan_arch(device->kmod.dev->props.gpu_id);\n',
    '   unsigned arch = pan_arch(device->kmod.dev->props.gpu_id);\n\n'
    '   vk_android_request_cpu_usable_swapchain_buffers();\n'
    '   if (arch >= 5)\n'
    '      vk_android_request_linear_swapchain_buffers_on_mediatek();\n'
)

print("Applied Faux123 1.1.9 MediaTek AHB usage behavior.")
