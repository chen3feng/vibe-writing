# 二进制移植与跨架构翻译工具全景盘点

> 从浏览器模拟器到硬件辅助二进制翻译——一份让软件超越原生架构的工具清单。

## 引言

在并非为其编译的硬件上运行软件，是计算机领域最迷人的挑战之一。数十年来，工程师们开发了令人印象深刻的工具阵列——从简单的解释器到硬件辅助翻译器——来弥合不兼容的指令集和操作系统之间的鸿沟。

本文按技术路线和使用场景，系统梳理当前主要的二进制移植与跨架构翻译工具。

## 一、用户态二进制翻译器

这类工具在宿主操作系统内将单个程序从一种 CPU 架构翻译到另一种，无需模拟整台机器。

### Box64 / Box86

**Box64** 是一个轻量级的开源 x86_64→ARM64 动态二进制翻译器，运行在 Linux 上。由法国开发者 **ptitSeb**（Sébastien Chevalier）创建，最初在 Pandora 掌机等小型 ARM 开发板上起步。

- **工作原理**：Box64 是一个独立的可执行文件，包裹 x86 程序运行。通过 Linux 的 `binfmt_misc` 机制，可以注册为 x86 ELF 二进制文件的默认处理器，使执行过程对用户透明。
- **库包装（Library Wrapping）**：Box64 性能的关键。它不翻译每一个库调用，而是拦截对常见本地库（`libc`、`libGL`、`libSDL`）的调用，重定向到宿主的 ARM64 原生版本。这意味着图形渲染和系统调用以原生速度运行。
- **JIT 编译**：x86 指令被动态翻译为 ARM64 机器码并缓存复用。

Box86 是其 32 位对应版本，用于 x86→ARM32 翻译。

### FEX-Emu

**FEX-Emu** 是 Box64 的一个更"学院派"的替代方案，采用清晰的三阶段编译器架构：

1. **前端**：将 x86/x86_64 指令解码为架构无关的**中间表示（IR）**。
2. **优化器**：对 IR 进行优化（死代码消除、常量折叠）。
3. **后端**：生成优化的 ARM64（或潜在的 RISC-V）机器码。

FEX 提供更深层的系统集成——它 hook 了 `execve()` 系统调用，使 x86 程序可以直接启动而无需包装器。它还处理 x86 复杂的内存寻址模式（如 `[RAX + RBX * 4 + 0x123]`），将其分解为多条 ARM 指令并仔细优化。

2026 年，FEX 已成为 Linux-on-ARM 生态系统的关键组件，尤其是在 Valve 赞助的游戏掌机上。

### Apple Rosetta 2

**Rosetta 2** 是 Apple 用于在 Apple Silicon（M 系列芯片）上运行 x86_64 macOS 应用的二进制翻译器，被广泛认为是二进制翻译的黄金标准。

- **AOT（提前编译）翻译**：安装 x86 应用时，macOS 在后台静默地将整个二进制文件翻译为 ARM64。当你启动它时，CPU 运行的几乎是纯 ARM 代码。
- **JIT 回退**：对于运行时生成代码的程序（如 JavaScript 引擎），Rosetta 2 回退到即时翻译。
- **硬件 TSO 支持**：秘密武器。Apple M 系列芯片包含一个硬件开关（`ACTLR_EL1.TSO`），强制 ARM 核心遵循 x86 的严格内存排序（Total Store Ordering）。这消除了昂贵的软件内存屏障需求，将翻译开销降至接近零。
- **系统库直通**：对 macOS 框架（Cocoa、Metal）的调用完全绕过翻译，直接调用原生 ARM64 库。

结果：翻译后的应用通常能达到原生性能的 **70–90%**。

### Microsoft XTA（x86-to-Arm）

Windows on ARM 使用 **XTA**，一个内核级二进制翻译引擎（`xta.dll`），在运行时将 x64 代码翻译为 ARM64。

- **代码缓存**：翻译后的代码块被缓存到磁盘，后续启动接近原生速度。
- **Arm64EC（Emulation Compatible）**：一种混合 ABI，允许原生 ARM64 代码和模拟的 x64 代码在同一进程中共存。系统 DLL（`ntdll.dll`、`kernel32.dll`）以原生 ARM64 版本加载，而应用逻辑在模拟模式下运行。
- **硬件协作**：高通骁龙 X Elite 包含硬件 TSO 支持和优化的标志位映射，类似于 Apple 的方案。

Arm64EC 的权衡：它牺牲了一些 ARM64 性能（参数传递的寄存器使用从 8 个减少到 4 个，寄存器集受限），换取与 x64 代码的无缝互操作。

## 二、Windows 兼容层

### Wine（Wine Is Not an Emulator）

**Wine** 在运行时将 Windows API 调用翻译为 POSIX/Linux 等价调用。它不模拟 CPU 指令——它为操作系统接口提供兼容层。

- 在 Linux 之上实现 Windows 系统调用、DLL 加载、注册表和 COM 基础设施。
- 提供 x86 和 ARM64 两种构建版本。在 ARM64 上运行时，Wine 处理 API 翻译，而另一个工具（Box64 或 FEX）处理指令翻译。

### Winlator

**Winlator** 是一个 Android 应用，将多种开源技术组合成完整的技术栈，用于在 ARM 手机上运行 Windows x86 游戏：

| 层级 | 技术 | 用途 |
|------|------|------|
| CPU 翻译 | Box64 / FEX-Emu | x86 → ARM64 指令翻译 |
| OS 兼容 | Wine | Windows API → Linux API |
| 图形 | DXVK + Turnip/Mesa | DirectX → Vulkan |
| 容器 | PRoot | 无需 root 的 Linux 文件系统 |
| 显示 | Xvnc / Wayland | 在 Android 上渲染 GUI |

### Proton（Valve）

**Proton** 是 Valve 为 Linux 上的 Steam 打造的集成层，组合了 Wine、DXVK、VKD3D-Proton（用于 DirectX 12）和各种补丁。它本身不是二进制翻译器，但却是这些技术在规模化部署上最成功的案例，驱动着 Steam Deck 的整个 Windows 游戏库。

### Hangover

**Hangover** 将 Wine 与二进制翻译器（FEX 或 Box64）桥接，在 ARM64 Linux 上运行 x86 Windows 应用。截至 11.0 版本，它提供无缝集成，不再依赖 QEMU。

### WineVDM（otvdm）

一个专门的工具，使 64 位 Windows 能够运行 **16 位** Windows 3.1 时代的程序——对于没有现代替代品的遗留工业和医疗软件至关重要。

## 三、全系统模拟器

这类工具模拟整台计算机，包括 CPU、内存和外围硬件。

### QEMU（Quick Emulator）

由 **Fabrice Bellard**（同时也是 FFmpeg 的作者）创建，QEMU 是模拟领域的瑞士军刀。

- **TCG（Tiny Code Generator）**：三阶段翻译引擎（前端 → IR → 后端），将客户机指令转换为宿主机指令。优先考虑快速编译而非最优代码生成。
- **两种模式**：
  - **用户态模拟**：翻译单个二进制文件的指令，将系统调用转发到宿主内核（类似 Box64）。
  - **全系统模拟**：模拟整台 PC——CPU、内存、IDE 控制器、VGA、网卡等。可以启动完整的操作系统。
- **KVM 加速**：当宿主和客户机架构相同时（如 x86 on x86），QEMU 委托给硬件虚拟化（Intel VT-x / AMD-V）以获得接近原生的性能。

### UTM

**UTM** 是 QEMU 的 macOS/iOS GUI 封装，增加了：
- Apple **Hypervisor.framework** 集成，在 Apple Silicon 上实现原生速度的 ARM64 虚拟机。
- SPICE 协议，支持剪贴板共享和自适应分辨率。
- 针对 iOS 代码签名限制的 JIT 变通方案。

### JSLinux

同样出自 Fabrice Bellard 之手，**JSLinux** 是一个用 JavaScript/WebAssembly 编写的完整 PC 模拟器，在浏览器中运行。它模拟 x86、RISC-V 和 ARM64 CPU，配备中断控制器、定时器和 VirtIO 网络。可以启动 Linux、Windows 2000 甚至 Windows XP。

### v86 / Copy.sh

**v86** 是一个开源的浏览器端 x86 PC 模拟器，用 Rust 编写并编译为 WebAssembly。主要特性：
- 完整的 Intel 80386+ 指令集模拟
- 硬件模拟：IDE、PS/2、Sound Blaster 16、NE2000 网卡
- **快照/恢复**：保存并即时恢复完整的虚拟机状态——实现在浏览器标签页中"即时启动"Windows 98
- WebSocket 网络代理，从虚拟机内部实现真正的互联网访问

## 四、浏览器端模拟器

### DOSBox + Emscripten（JS-DOS）

在浏览器中运行 DOS 游戏的经典方案：
1. **DOSBox**（C++）模拟带 VGA 和 Sound Blaster 的 x86 PC
2. **Emscripten** 将 DOSBox 编译为 WebAssembly
3. 浏览器通过 Canvas/WebGL 渲染，通过 Web Audio API 播放音频

**JS-DOS** 是最流行的封装库，将部署简化为几行 JavaScript。

### 游戏主机模拟器（Web 版）

| 主机 | 项目 | 技术 |
|------|------|------|
| NES | JSNES | 纯 JavaScript，6502 CPU 模拟 |
| Game Boy | WasmBoy | AssemblyScript → WebAssembly |
| SNES | Snes9x.js | Emscripten + C++ |
| GBA | IodineGBA | JavaScript + WebGL |
| 多系统 | RetroArch Web | Emscripten + Libretro 核心 |

## 五、原生游戏主机模拟器

### 解释执行 vs. 动态重编译

- **解释执行**：逐条读取并执行指令。简单但慢。早期 NES/GB 模拟器和 **MAME**（为了街机精确性）使用此方式。
- **动态重编译（JIT）**：将客户机代码块翻译为宿主机器码并缓存。现代高性能模拟器使用此方式。

### 代表性项目

| 主机 | 模拟器 | 技术 |
|------|--------|------|
| NES | Mesen | 高精度解释执行 |
| SNES | Snes9x | 解释执行 + 优化 |
| N64 | Mupen64Plus | 动态重编译 |
| GameCube/Wii | **Dolphin** | JIT，模拟器工程的标杆 |
| Wii U | Cemu | JIT，开源 |
| Switch | Ryujinx, Eden | JIT + GPU 着色器翻译 |
| PS3 | RPCS3 | JIT + Vulkan 渲染 |
| PSP | PPSSPP | JIT |

### FPGA 硬件模拟

**MiSTer FPGA** 和 **Analogue Pocket** 采用了截然不同的方案：它们不使用软件模拟，而是对 FPGA 芯片重新编程，物理重建原始主机的电路。结果：**零延迟**，周期精确的复现。

## 六、硬件辅助翻译特性

现代 ARM 处理器越来越多地包含专门为加速 x86 二进制翻译而设计的硬件特性：

| 特性 | Apple M 系列 | 高通骁龙 X Elite |
|------|-------------|-----------------|
| 硬件 TSO 模式 | ✅ `ACTLR_EL1.TSO` | ✅ Oryon CPU 核心 |
| 标志位加速 | 通过宽流水线 | 专用优化 |
| TLB 优化 | 集成 | 上下文切换感知 |
| 内存屏障消除 | 硬件级 | 硬件级 |

这些特性将二进制翻译从约 50% 的性能损失转变为约 10–20% 的损失，使翻译后的软件在日常使用中切实可行。

## 七、实验性方向：AI 辅助二进制翻译

Google Research 已开始尝试使用 **LLM 辅助二进制翻译**。其思路不是逐条翻译指令，而是让 AI "理解"代码块的语义意图（例如"这是一个 FFT 算法"），然后生成功能等价但充分利用目标架构特性的优化原生代码。这有可能产生**超越原始代码性能**的翻译结果。

## 总结

二进制移植的技术版图涵盖了极其广泛的方案：

- **轻量级用户态翻译器**（Box64、FEX-Emu）用于运行单个程序
- **系统兼容层**（Wine、Proton）用于 API 翻译
- **全系统模拟器**（QEMU、JSLinux）用于运行完整操作系统
- **软硬件协同设计**（Rosetta 2、XTA + Arm64EC）用于近乎透明的架构迁移
- **FPGA 重建**用于周期精确的硬件复现

趋势很明确："原生"与"翻译"执行之间的界限正在迅速消融，这得益于硬件 TSO 支持、AOT 编译和日益精密的 JIT 引擎。在 2026 年，用户可以在 ARM Android 手机上运行 x86 Windows 游戏，在浏览器标签页中启动 Windows XP，或者在 Apple Silicon 上运行 macOS x86 应用，几乎感觉不到开销。

这些工具背后的工程师们——从 Fabrice Bellard 的独行天才，到 ptitSeb 充满热情的开源工作，再到 Apple 垂直整合的芯片团队——代表了现代计算领域最令人印象深刻的技术成就。
