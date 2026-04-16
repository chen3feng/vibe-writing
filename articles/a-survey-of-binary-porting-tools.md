# A Survey of Binary Porting and Cross-Architecture Translation Tools

> From browser-based emulators to hardware-assisted binary translation — a comprehensive inventory of tools that let software transcend its native architecture.

## Introduction

Running software on hardware it was never compiled for is one of computing's most fascinating challenges. Over the decades, engineers have developed an impressive array of tools — from simple interpreters to hardware-assisted translators — that bridge the gap between incompatible instruction sets and operating systems.

This article surveys the major binary porting and cross-architecture translation tools available today, organized by their technical approach and use case.

## 1. User-Mode Binary Translators

These tools translate individual programs from one CPU architecture to another, running within the host OS without emulating an entire machine.

### Box64 / Box86

**Box64** is a lightweight, open-source x86_64-to-ARM64 dynamic binary translator for Linux. Created by **ptitSeb** (Sébastien Chevalier), a French developer who started the project on tiny ARM boards like the Pandora handheld.

- **How it works**: Box64 is a standalone executable that wraps x86 programs. Through Linux's `binfmt_misc`, it can be registered as the default handler for x86 ELF binaries, making execution transparent.
- **Library Wrapping**: The key to Box64's performance. Instead of translating every library call, it intercepts calls to common native libraries (`libc`, `libGL`, `libSDL`) and redirects them to the host's ARM64 versions. This means graphics rendering and system calls run at native speed.
- **JIT compilation**: x86 instructions are dynamically translated to ARM64 machine code and cached for reuse.

Box86 is its 32-bit counterpart for x86-to-ARM32 translation.

### FEX-Emu

**FEX-Emu** is a more "academic" alternative to Box64, designed with a clean three-stage compiler architecture:

1. **Frontend**: Decodes x86/x86_64 instructions into an architecture-independent **Intermediate Representation (IR)**.
2. **Optimizer**: Performs optimizations on the IR (dead code elimination, constant folding).
3. **Backend**: Generates optimized ARM64 (or potentially RISC-V) machine code.

FEX offers deeper system integration — it hooks into `execve()` so x86 programs can be launched directly without a wrapper. It also handles x86's complex memory addressing modes (e.g., `[RAX + RBX * 4 + 0x123]`) by decomposing them into multiple ARM instructions with careful optimization.

In 2026, FEX has become a key component in Linux-on-ARM ecosystems, especially for Valve-sponsored gaming handhelds.

### Apple Rosetta 2

**Rosetta 2** is Apple's binary translator for running x86_64 macOS apps on Apple Silicon (M-series) chips. It is widely regarded as the gold standard of binary translation.

- **AOT (Ahead-of-Time) translation**: When an x86 app is installed, macOS silently translates the entire binary to ARM64 in the background. By the time you launch it, the CPU runs nearly pure ARM code.
- **JIT fallback**: For programs that generate code at runtime (e.g., JavaScript engines), Rosetta 2 falls back to just-in-time translation.
- **Hardware TSO support**: The secret weapon. Apple's M-series chips include a hardware switch (`ACTLR_EL1.TSO`) that forces the ARM cores to follow x86's strict memory ordering (Total Store Ordering). This eliminates the need for expensive software memory barriers, reducing translation overhead to near zero.
- **System library passthrough**: Calls to macOS frameworks (Cocoa, Metal) bypass translation entirely, invoking native ARM64 libraries directly.

Result: translated apps often achieve **70–90%** of native performance.

### Microsoft XTA (x86-to-Arm)

Windows on ARM uses **XTA**, a kernel-level binary translation engine (`xta.dll`) that translates x64 code to ARM64 at runtime.

- **Code caching**: Translated code blocks are cached to disk, so subsequent launches approach native speed.
- **Arm64EC (Emulation Compatible)**: A hybrid ABI that allows native ARM64 code and emulated x64 code to coexist within a single process. System DLLs (`ntdll.dll`, `kernel32.dll`) are loaded as native ARM64 versions, while application logic runs in emulated mode.
- **Hardware cooperation**: Qualcomm's Snapdragon X Elite includes hardware TSO support and optimized flag-bit mapping, similar to Apple's approach.

The trade-off of Arm64EC: it sacrifices some ARM64 performance (reduced register usage from 8 to 4 for parameter passing, restricted register set) in exchange for seamless interoperability with x64 code.

## 2. Windows Compatibility Layers

### Wine (Wine Is Not an Emulator)

**Wine** translates Windows API calls to POSIX/Linux equivalents at runtime. It does not emulate CPU instructions — it provides a compatibility layer for the operating system interface.

- Implements Windows system calls, DLL loading, registry, and COM infrastructure on top of Linux.
- Available in both x86 and ARM64 builds. When running on ARM64, Wine handles the API translation while a separate tool (Box64 or FEX) handles the instruction translation.

### Winlator

**Winlator** is an Android app that combines multiple open-source technologies into a complete stack for running Windows x86 games on ARM phones:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| CPU translation | Box64 / FEX-Emu | x86 → ARM64 instruction translation |
| OS compatibility | Wine | Windows API → Linux API |
| Graphics | DXVK + Turnip/Mesa | DirectX → Vulkan |
| Container | PRoot | Linux filesystem without root |
| Display | Xvnc / Wayland | GUI rendering on Android |

### Proton (Valve)

**Proton** is Valve's integration layer for Steam on Linux, combining Wine, DXVK, VKD3D-Proton (for DirectX 12), and various patches. It is not a binary translator itself, but the most successful deployment of these technologies at scale, powering the Steam Deck's entire Windows game library.

### Hangover

**Hangover** bridges Wine with binary translators (FEX or Box64) to run x86 Windows applications on ARM64 Linux. As of version 11.0, it provides seamless integration without depending on QEMU.

### WineVDM (otvdm)

A specialized tool that enables 64-bit Windows to run **16-bit** Windows 3.1-era programs — critical for legacy industrial and medical software that has no modern replacement.

## 3. Full System Emulators

These tools emulate an entire computer, including CPU, memory, and peripheral hardware.

### QEMU (Quick Emulator)

Created by **Fabrice Bellard** (also the author of FFmpeg), QEMU is the Swiss Army knife of emulation.

- **TCG (Tiny Code Generator)**: A three-stage translation engine (frontend → IR → backend) that converts guest instructions to host instructions. Prioritizes fast compilation over optimal code generation.
- **Two modes**:
  - **User-mode emulation**: Translates a single binary's instructions, forwarding syscalls to the host kernel (similar to Box64).
  - **Full system emulation**: Emulates an entire PC — CPU, memory, IDE controller, VGA, NIC, etc. Can boot complete operating systems.
- **KVM acceleration**: When host and guest architectures match (e.g., x86 on x86), QEMU delegates to hardware virtualization (Intel VT-x / AMD-V) for near-native performance.

### UTM

**UTM** is a macOS/iOS GUI wrapper around QEMU, adding:
- Apple **Hypervisor.framework** integration for native-speed ARM64 VMs on Apple Silicon.
- SPICE protocol for clipboard sharing and adaptive resolution.
- JIT workarounds for iOS's code signing restrictions.

### JSLinux

Also by Fabrice Bellard, **JSLinux** is a full PC emulator written in JavaScript/WebAssembly that runs in the browser. It emulates x86, RISC-V, and ARM64 CPUs, complete with interrupt controllers, timers, and VirtIO networking. It can boot Linux, Windows 2000, and even Windows XP.

### v86 / Copy.sh

**v86** is an open-source x86 PC emulator for the browser, written in Rust compiled to WebAssembly. Key features:
- Full Intel 80386+ instruction set emulation
- Hardware emulation: IDE, PS/2, Sound Blaster 16, NE2000 NIC
- **Snapshot/restore**: Save and instantly restore complete VM states — enabling "instant boot" of Windows 98 in a browser tab
- WebSocket networking proxy for real internet access from within the VM

## 4. Browser-Based Emulators

### DOSBox + Emscripten (JS-DOS)

The classic approach to running DOS games in browsers:
1. **DOSBox** (C++) emulates an x86 PC with VGA and Sound Blaster
2. **Emscripten** compiles DOSBox to WebAssembly
3. The browser renders via Canvas/WebGL and plays audio via Web Audio API

**JS-DOS** is the most popular wrapper library, simplifying deployment to a few lines of JavaScript.

### Game Console Emulators (Web)

| Console | Project | Technology |
|---------|---------|-----------|
| NES | JSNES | Pure JavaScript, 6502 CPU emulation |
| Game Boy | WasmBoy | AssemblyScript → WebAssembly |
| SNES | Snes9x.js | Emscripten + C++ |
| GBA | IodineGBA | JavaScript + WebGL |
| Multi-system | RetroArch Web | Emscripten + Libretro cores |

## 5. Native Game Console Emulators

### Interpretation vs. Dynamic Recompilation

- **Interpretation**: Read and execute each instruction one by one. Simple but slow. Used by early NES/GB emulators and **MAME** (for arcade accuracy).
- **Dynamic Recompilation (JIT)**: Translate blocks of guest code to host machine code and cache them. Used by modern high-performance emulators.

### Notable Projects

| Console | Emulator | Technique |
|---------|----------|-----------|
| NES | Mesen | High-accuracy interpretation |
| SNES | Snes9x | Interpretation + optimizations |
| N64 | Mupen64Plus | Dynamic recompilation |
| GameCube/Wii | **Dolphin** | JIT, the benchmark of emulator engineering |
| Wii U | Cemu | JIT, open-source |
| Switch | Ryujinx, Eden | JIT + GPU shader translation |
| PS3 | RPCS3 | JIT + Vulkan rendering |
| PSP | PPSSPP | JIT |

### FPGA Hardware Emulation

**MiSTer FPGA** and **Analogue Pocket** take a radically different approach: instead of software emulation, they reprogram FPGA chips to physically recreate the original console's circuits. Result: **zero latency**, cycle-accurate reproduction.

## 6. Hardware-Assisted Translation Features

Modern ARM processors increasingly include hardware features specifically designed to accelerate x86 binary translation:

| Feature | Apple M-series | Qualcomm Snapdragon X Elite |
|---------|---------------|----------------------------|
| Hardware TSO mode | ✅ `ACTLR_EL1.TSO` | ✅ Oryon CPU cores |
| Flag-bit acceleration | Via wide pipelines | Dedicated optimization |
| TLB optimization | Integrated | Context-switch aware |
| Memory barrier elimination | Hardware-level | Hardware-level |

These features transform binary translation from a ~50% performance penalty to a ~10–20% penalty, making translated software practical for everyday use.

## 7. Experimental: AI-Assisted Binary Translation

Google Research has begun experimenting with using **LLMs to assist binary translation**. Instead of translating instructions one-by-one, the idea is to have an AI "understand" the semantic intent of a code block (e.g., "this is an FFT algorithm") and generate optimized native code that is functionally equivalent but takes full advantage of the target architecture's features. This could potentially produce translated code that **outperforms** the original.

## Conclusion

The binary porting landscape spans an enormous range of approaches:

- **Lightweight user-mode translators** (Box64, FEX-Emu) for running individual programs
- **System compatibility layers** (Wine, Proton) for API translation
- **Full system emulators** (QEMU, JSLinux) for running entire operating systems
- **Hardware-software co-design** (Rosetta 2, XTA + Arm64EC) for near-transparent architecture migration
- **FPGA recreation** for cycle-perfect hardware reproduction

The trend is clear: the boundary between "native" and "translated" execution is rapidly dissolving, driven by hardware TSO support, AOT compilation, and increasingly sophisticated JIT engines. In 2026, a user can run x86 Windows games on an ARM Android phone, boot Windows XP in a browser tab, or run macOS x86 apps on Apple Silicon with barely noticeable overhead.

The engineers behind these tools — from Fabrice Bellard's solo genius to ptitSeb's passionate open-source work to Apple's vertically integrated silicon team — represent some of the most impressive technical achievements in modern computing.
