# FCLDriverPlugin

FoldCraftLauncher（FCL）的自定义 Vulkan 驱动插件模板。把驱动 `.so` 按本模板打包成 APK 安装，即可在 FCL 的「版本设置 → 驱动」中选择使用。

A driver plugin template for FoldCraftLauncher. Package a Vulkan driver's `.so` files into an APK with this template and select it in FCL under *Version Settings → Driver*.

## 插件契约 / Plugin contract

FCL 通过插件 APK 的 manifest metaData 识别驱动插件：

FCL identifies driver plugins through manifest metadata:

| metaData | 说明 / Description | 示例 / Example | 缺省 / Default |
|---|---|---|---|
| `fclPlugin` | 固定为 `true` / must be `true` | `true` | 必填 / required |
| `driver` | 启动器内显示的驱动名 / display name in the launcher | `Turnip 24.3.2`、`PanVK 26.3` | 必填 / required |
| `driver_lib` | 驱动库文件名，须存在于 APK 的 jniLibs 中 / driver library file name, must exist in the APK's jniLibs | `libvulkan_freedreno.so`、`libvulkan_panfrost.so` | `libvulkan_freedreno.so` |
| `driver_gpu` | 驱动适配的 GPU 家族 / the GPU family the driver targets：`adreno` / `mali` / `any` | panvk 填 `mali` | `adreno` |

以上值均经 `app/build.gradle.kts` 的 `manifestPlaceholders` 配置，模板已内置 Turnip 示例值，开箱即可构建。

All values are configured via `manifestPlaceholders` in `app/build.gradle.kts`. The template ships with Turnip values and builds out of the box.

## 制作驱动插件 / Building a driver plugin

1. **放入驱动库 / Add the driver libraries**
   把驱动 `.so` 放入 `app/src/main/jniLibs/arm64-v8a/`，驱动依赖的其他 `.so` 一并放入。
   Put the driver `.so` into `app/src/main/jniLibs/arm64-v8a/`, together with any `.so` it depends on.
   - Turnip（Adreno）：`libvulkan_freedreno.so`
   - panvk（Mali）：**`libvulkan_panfrost.so`**（Mesa panvk 的 ICD 库名沿用 panfrost，注意不是 `libvulkan_panvk.so` / Mesa's panvk ICD is named after panfrost, not `libvulkan_panvk.so`）

2. **修改 `app/build.gradle.kts` / Edit `app/build.gradle.kts`**

   ```kotlin
   //应用名
   //app name
   resValue("string","app_name","PanVK 26.3")
   //包名后缀（每个驱动唯一，多个插件可共存）
   //package name Suffix (unique per driver so multiple plugins can coexist)
   applicationIdSuffix = ".panvk263"

   manifestPlaceholders["driver"] = "PanVK 26.3"
   manifestPlaceholders["driverLib"] = "libvulkan_panfrost.so"
   manifestPlaceholders["driverGpu"] = "mali"
   ```

3. **构建并安装 / Build and install**

   ```bash
   ./gradlew assembleRelease
   ```

   安装生成的 APK，在 FCL「版本设置 → 驱动」中选择该驱动。
   Install the APK and pick the driver in FCL under *Version Settings → Driver*.

## FCL 如何加载驱动 / How FCL loads the driver

- FCL 把插件解压出的 native 库目录作为 `DRIVER_PATH` 传入游戏进程，linkerhook 拦截 libvulkan 加载器的 `android_dlopen_ext`，按 `driver_lib` 从该目录加载驱动库。
  FCL passes the plugin's extracted native library directory as `DRIVER_PATH` to the game process; a linker hook intercepts the Vulkan loader's `android_dlopen_ext` and loads the library named by `driver_lib` from that directory.
- 仅当设备 GPU 家族与 `driver_gpu` 匹配时才启用自定义驱动路径，否则回落系统驱动。
  The custom driver path is only engaged when the device's GPU family matches `driver_gpu`; otherwise the system driver is used.
- 启动前的「检测 Vulkan」会按实际枚举到的版本/扩展/特性评估各 MC 版本的支持情况；驱动初始化失败时自动回落系统驱动并提示。
  The pre-launch Vulkan check evaluates per-MC-version support from the actually enumerated version/extensions/features; if driver initialization fails, FCL falls back to the system driver and says so.
- `driver_lib` / `driver_gpu` 需要支持自定义驱动加载的 FCL 版本（仅内置 Turnip 的旧版本会忽略这两个键）。
  `driver_lib` / `driver_gpu` require an FCL build with generic custom driver support (older builds that only bundle Turnip ignore these keys).

## 参考 / Reference

- Turnip 驱动构建 / Turnip builds: [K11MCH1/AdrenoToolsDrivers](https://github.com/K11MCH1/AdrenoToolsDrivers)
- panvk（Mali，kbase 内核）: [zenithblue-oss/panvk-kbase-android](https://github.com/zenithblue-oss/panvk-kbase-android)、[FristOneRR-Panvk-Driver](https://github.com/FristOneRR/FristOneRR-Panvk-Driver)
  （上游 Mesa panvk 仅支持 panfrost/panthor 主线内核；量产 Mali 设备为 mali_kbase，需使用上述移植构建 / upstream Mesa panvk only supports the panfrost/panthor mainline kernel drivers, while production Mali devices ship mali_kbase — use the kbase ports above）
- 相关 issue / Related issues: [FoldCraftLauncher #1614](https://github.com/FCL-Team/FoldCraftLauncher/issues/1614)、[#1937](https://github.com/FCL-Team/FoldCraftLauncher/issues/1937)
