# [设计] `combined_cc_library`：把多个 C++ 静态库合并成一个可分发的复合库

## 背景

我们经常需要把内部的多个 `cc_library`（以及部分第三方依赖）打包成**一个**可对外交付的库——类似 Java 的 Fat JAR / Shaded JAR，让使用方一次链接、零配置即可使用。

C++ 没有 Fat JAR 这样的标准产物，社区也没有统一术语。常见说法各有侧重：

- **Fully Statically Linked Binary**：最终可执行文件全静态链接（`-static`），对标"有 JVM 就能跑"，但这是程序不是库。
- **Combined / Bundle / Monolithic / Self-contained Static Library**：把多个 `.a` / `.lib` 合并成一个库。
- ⚠️ **Fat Static Library / Fat Binary 这个词不能用**：在 Apple 生态里 "Fat Library" 已被**多架构库**（x86_64 + arm64，用 `lipo` 合并）占用，会引起严重歧义。

合并静态库也不是简单拼接——`.a` 本质是 `.o` 的归档（archive），需要用 `ar` / `libtool` / `lib.exe` 拆开再重打包。

## 命名建议

调研后，规则名与产物名分开考虑：

| 用途 | 推荐 | 说明 |
|------|------|------|
| **规则/宏名（前缀）** | `combined_cc_library` | 与 `static_cc_library` / `shared_cc_library` 同构，描述"物理属性"，结构清晰；避免 `combined_standalone_*` 这种形容词叠形容词 |
| **产物 target 名（后缀）** | `xxx_combined` / `xxx_standalone` | `_combined` 强调"多合一来源"；`_standalone` 强调"自包含、无外部依赖、开箱即用"，对外 SDK 含金量更高 |

语义边界（重要，影响对外承诺）：

- `_combined` = "我合并了内部模块"，**不保证**消除了外部依赖，使用方可能还要自己链 `protobuf` / `openssl`。
- `_standalone` = "你链我就够了"，必须**做绝**：把第三方依赖也吞进去且做符号隔离，否则名不副实。

**结论**：规则名用 `combined_cc_library`；是否对外宣称 standalone，取决于是否真正实现了符号隔离（见功能 7）。

## 目标

提供一个自定义 Starlark 规则 `combined_cc_library`，对外暴露简洁接口，底层用 `ar` / `libtool` / `lib.exe` + `cp` + 符号工具完成打包。Bazel 原生没有此规则（其哲学是细粒度依赖、不鼓励中间二进制合并），但对外发布 C++ SDK 的团队几乎刚需，业界普遍以自定义宏实现。

目标接口形态：

```python
combined_cc_library(
    name = "universal_sdk",
    deps = ["//src:core", "//third_party:jsoncpp"],
    exclude_deps = ["//third_party:gtest"],     # 1. 排除依赖
    hdrs = ["//src:api.h"],                       # 2. 导出并扁平化头文件
    generate_umbrella_header = True,              # 3. 自动生成伞形头文件
    hide_internal_symbols = True,                 # 4. 符号隐藏（防冲突）
    linkopts = ["-lpthread"],                     # 5. 传递系统级链接参数
    generate_cmake_config = True,                 # 6. 生成 CMake / pkg-config 接入文件
)
```

## 核心功能清单

### 1. 合并静态库（必需）
收集 `deps` 全部传递依赖的 `.o` / `.a`，平台对应工具合并为单一库。

### 2. 排除依赖 `exclude_deps`（必需）
最常见场景：合并 A、B，但 A 依赖的 `liblog.a` 使用方环境自带，必须剔除避免 `multiple definition`。
- **策略 A（首选）链接期拓扑过滤**：遍历依赖树，合并前计算 `deps - exclude_deps` 差集，砍掉匹配的 `.o` / `.a`。
- **策略 B 符号剥离**：输出端用 `objcopy` / linker script 擦除被排除库的符号。

### 3. 导出并扁平化头文件 `hdrs`（必需）
只给二进制不给头文件无法编译。需要：
- 显式声明哪些是公开头文件（`hdrs` / `public_hdrs`），其余私有头文件**一律不复制**。
- **扁平化（Flattening）**：把公开头文件统一复制到干净的 `include/`，使用方只需一个 `-Iinclude`，避免 `#include "modules/audio/src/impl/codec.h"` 这种深路径泄漏。

### 4. 伞形头文件 `generate_umbrella_header`（可选）
模块多时自动生成 `xxx_combined.h`，内部 `#include` 全部公开头文件，使用方一行 `#include <sdk.h>` 解锁全部功能（对标 OpenCV `opencv2/opencv.hpp`）。

### 5. 传递性编译/链接参数合并与过滤
- `copts` / `defines`（如 `-DENABLE_DEBUG=1`）需自动随依赖合并；**被 `exclude_deps` 剔除的库，其宏也必须同步剔除**，否则引发未定义行为。
- 系统库（`-lpthread` / `-lm` / `-ldl`）打不进静态库，规则需用 `linkopts` 自动收集并写入元数据，使用方无需盲猜。

### 6. 元数据生成 `generate_cmake_config` / `generate_pkg_config`
自动产出 `MySDKConfig.cmake` 或 `.pc`，让使用方 `find_package(MySDK REQUIRED)` 一行接入，自动配好头文件路径、库路径、系统依赖。

### 7. 符号隐藏（防冲突，对外 standalone 的前提）
把不得不打包进去的第三方库（如某版本 `libjpeg`）符号物理隐藏，免疫与使用方的符号冲突。**这是各平台差异最大的部分，见下节。**

### 8. 可选输出动态库 `linkshared`
一键切换 `.a`/`.lib` 与 `.so`/`.dll`。Windows 下生成动态库时需自动处理 `__declspec(dllexport)`，同时产出 `.dll` 和导入库 `.lib`。

## 跨平台实现矩阵

| 维度 | Linux (GCC/Clang) | Windows (MSVC) | macOS (Clang/Xcode) |
|------|-------------------|----------------|---------------------|
| 静态库合并 | `ar` | `lib.exe` | `libtool -static` |
| 静态库符号隔离 | `objcopy --localize-hidden` | 不支持，改用 `.def` 白名单过滤 | `strip` + 符号白名单 |
| 动态库导出控制 | `-fvisibility=hidden` + `__attribute__((visibility("default")))` | `__declspec(dllexport)`（默认不导出） | `-Wl,-exported_symbols_list` |
| 黑名单方式 | linker version script 的 `local:`（支持通配符） | `.def` 只支持白名单 `EXPORTS`，靠覆盖屏蔽；或编译期宏置空导出宏 | `-Wl,-unexported_symbols_list` |
| 多架构 | 一般分包 | 区分 x64/ARM64 目录 | `lipo` 融合 |
| 最终交付形态 | `tar.gz`（lib + include） | `zip`（dll + lib + include） | `.framework` / `.xcframework` |

### 符号隔离的关键细节

- **Linux**：编译期用 `-fvisibility=hidden` 把第三方符号默认标 `hidden`，合并后 `objcopy --localize-hidden` 把所有 `hidden` 全局符号降级为 `local`（`nm` 里从 `T` 变 `t`），外部彻底不可见。
- **避免手写 mangled name**：不要手工去凑 `_ZN11MyPublicAPI...`。自动化方案：
  - 公开 C 接口用 `extern "C"`（无 name mangling）；
  - 或构建期用 `nm` + `c++filt` 脚本按类名/命名空间自动生成白名单；
  - macOS 可逆向用**黑名单**（`nm | grep protobuf` 收集第三方符号前缀 → `-unexported_symbols_list`），无需知道自己公开符号叫什么。
- **Linux version script 通配符黑名单**最地道：
  ```
  { global: *MyPublicAPI*; local: *google::protobuf*; *Json::*; *; };
  ```
- **MSVC** 静态库无法像 Linux 那样降级符号。**上策**：改走 DLL（天然符号边界）；**下策**：必须交付 `.lib` 时，用 `.def` 白名单 + `/DEF`，或编译期把第三方导出宏 `-DPROTOBUF_EXPORT=` 置空。

## 私有头文件污染问题（重要设计决策）

公开头文件 `#include` 了私有头文件时，Bazel 靠"不声明在 `hdrs`"只能挡住第一层物理隔离；一旦公开头文件内部引用私有头文件（成员变量、继承、内联、模板），使用方编译直接 `file not found`。

**讨论结论：这不该由构建系统通过脚本自动"魔改"源码来解决。**

理由：
- 脚本删 `#include` 但不改后续用到私有类型的代码，必然 `unknown type` 报错。
- 真正需要前置声明 vs 必须暴露完整定义（值成员、内联、模板），只有库作者有完整语义判断；构建系统没有编译器级语义分析能力，瞎改引入更难排查的链接错误。
- 值成员 `PrivateHelper m_helper;`（非指针/引用）时，编译器物理上必须知道其大小，**任何脚本都无解**。

**权责划分**：

- **库作者负责**（架构层解决）：用 **Pimpl 模式**（`unique_ptr<Impl>` + 前置声明）或**纯虚接口类 + 工厂函数**（UE 的常见做法）从源头切断 `hdrs` 对 `srcs` 的 transitive include。
- **构建系统负责**（当"纪检委"，不当"擦屁股"的）：
  1. **沙盒严格审查**：编译外部使用方代码时故意藏起私有头文件，公开头文件一旦引用私有头文件立即编译失败，倒逼重构。
  2. **依赖合法性静态扫描**：用 Aspect / clang-tidy 在 PR 阶段扫描公开头文件，发现引用非公开 `hdrs` 直接打回。给出明确报错，例如：
     `[Build Error] Public header 'my_api.h' exposes private size-dependent type 'PrivateHelper'. Please refactor using Pimpl or virtual interface.`
  3. **最基础的搬运**：收集库作者处理好的 `public_hdrs` 扁平化到 `include/`，合并二进制到 `lib/`。

> 一句话：**架构的问题在架构层解决，不在工具层打补丁。** 让脚本智能改写 C++ 源码是吃力不讨好的伪需求。

## 待确认 / 开放问题

- [ ] 规则最终名定 `combined_cc_library`？产物后缀约定 `_combined` 还是 `_standalone`（取决于是否实现真符号隔离）？
- [ ] 第一期支持平台范围：先 Linux，还是 Linux + macOS + Windows 全覆盖？
- [ ] 符号隔离是否进第一期，还是先做"合并 + 排除 + 头文件导出"三件套？
- [ ] 是否复用现成方案（`bazel-distribution` / `rules_pkg` 等）而非完全自研？需评估对 `exclude_deps`、符号隔离的支持度。
- [ ] 上文若干平台命令的精确参数（如 macOS `strip` 白名单的确切 flag、`objcopy --localize-hidden` 行为）需在目标工具链版本上实测验证后再写进实现。

## 参考

- 命名歧义来源：Apple `lipo` / Fat Binary（多架构）。
- Bazel 社区实践：自定义 Starlark 宏 + `CcInfo` provider 收集 `.o`/头文件 + `genrule`/Action 调 `ar`；`bazel-distribution`、AOSP 的 `cc_library_static` 复合打包。
- 对标产物结构：
  ```
  outputs/
  ├── lib/libsdk_combined.a   # 去重、排除冲突依赖、隐藏第三方符号后的复合静态库
  └── include/
      ├── sdk_combined.h       # 伞形头文件
      └── *.h                  # 扁平化的公开接口
  ```

---

*本草稿由一次设计讨论整理而成，技术细节（尤其各平台命令的精确行为）以实测为准。*
