#!/usr/bin/env python3
"""Add deterministic diagnostics to the pinned Android PanVK WSI implementation."""
from pathlib import Path

p = Path("source/work/mesa/src/panfrost/vulkan/panvk_wsi.c")
s = p.read_text()

replacements = [
("""      if (AHardwareBuffer_allocate(&desc, &chain->images[i].ahb) != 0 || !chain->images[i].ahb) {
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return VK_ERROR_INITIALIZATION_FAILED;
      }""",
"""      int ahb_rc = AHardwareBuffer_allocate(&desc, &chain->images[i].ahb);
      if (ahb_rc != 0 || !chain->images[i].ahb) {
         mesa_loge("panvk-wsi-diag: stage=ahb_allocate index=%u rc=%d ahb=%p extent=%ux%u format=%u usage=0x%llx",
                   i, ahb_rc, chain->images[i].ahb, desc.width, desc.height,
                   desc.format, (unsigned long long)desc.usage);
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return VK_ERROR_INITIALIZATION_FAILED;
      }
      mesa_logi("panvk-wsi-diag: stage=ahb_allocate index=%u rc=0 ahb=%p extent=%ux%u stride=%u",
                i, chain->images[i].ahb, desc.width, desc.height, desc.stride);"""),
("""      if (result != VK_SUCCESS) {
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return result;
      }

      VkAndroidHardwareBufferPropertiesANDROID ahb_props""",
"""      if (result != VK_SUCCESS) {
         mesa_loge("panvk-wsi-diag: stage=create_image index=%u result=%d format=%u usage=0x%x extent=%ux%u",
                   i, result, ici.format, ici.usage, ici.extent.width, ici.extent.height);
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return result;
      }

      VkAndroidHardwareBufferPropertiesANDROID ahb_props"""),
("""      if (result != VK_SUCCESS) {
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return result;
      }

      uint32_t chosen_mi = 0;""",
"""      if (result != VK_SUCCESS) {
         mesa_loge("panvk-wsi-diag: stage=ahb_properties index=%u result=%d ahb=%p",
                   i, result, chain->images[i].ahb);
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return result;
      }
      mesa_logi("panvk-wsi-diag: stage=ahb_properties index=%u result=0 allocation=%llu memoryTypeBits=0x%x",
                i, (unsigned long long)ahb_props.allocationSize, ahb_props.memoryTypeBits);

      if (!ahb_props.memoryTypeBits) {
         mesa_loge("panvk-wsi-diag: stage=ahb_memory_types index=%u allocation=%llu memoryTypeBits=0\\n",
                   i, (unsigned long long)ahb_props.allocationSize);
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return VK_ERROR_INVALID_EXTERNAL_HANDLE;
      }

      uint32_t chosen_mi = 0;"""),
("""      if (result != VK_SUCCESS) {
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return result;
      }

      VkBindImageMemoryInfo bmi""",
"""      if (result != VK_SUCCESS) {
         mesa_loge("panvk-wsi-diag: stage=allocate_memory index=%u result=%d size=%llu memoryTypeIndex=%u",
                   i, result, (unsigned long long)mai.allocationSize, mai.memoryTypeIndex);
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return result;
      }

      VkBindImageMemoryInfo bmi"""),
("""      if (result != VK_SUCCESS) {
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return result;
      }
   }
   vk_android_set_owned_ahb(NULL);""",
"""      if (result != VK_SUCCESS) {
         mesa_loge("panvk-wsi-diag: stage=bind_image_memory index=%u result=%d image=%p memory=%p",
                   i, result, chain->images[i].base.image, chain->images[i].base.memory);
         panvk_android_swapchain_destroy(&chain->base, pAllocator);
         return result;
      }
      mesa_logi("panvk-wsi-diag: stage=swapchain_image_ready index=%u image=%p memory=%p",
                i, chain->images[i].base.image, chain->images[i].base.memory);
   }
   vk_android_set_owned_ahb(NULL);"""),
]

for old, new in replacements:
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one WSI anchor, found {count}: {old[:100]!r}")
    s = s.replace(old, new, 1)

p.write_text(s)
print("Instrumented Android WSI stages: AHardwareBuffer allocation, image creation, AHB properties, memory allocation, image bind.")
