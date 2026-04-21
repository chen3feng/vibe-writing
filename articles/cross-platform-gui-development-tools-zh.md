# GUI 开发三维地图：技术实现、目标平台与语言生态的正交切片（2026版）

> 不再用"桌面 vs 移动 vs Web"这种一刀切的旧分类。这一次，我们把所有主流 GUI 框架放进一张三轴坐标系：**怎么画（技术实现）、在哪跑（目标平台）、谁在用（语言生态）**——同一个框架在三章里各出现一次，每次讲一个不同的切面。

## 引言：为什么需要三条正交主线

GUI 开发的世界远比想象中复杂。在 Windows 这一座"老宅"里，微软堆叠了 20 多年的 GUI 框架全家桶；在跨平台领域，Tauri、Flutter、Avalonia 等新锐层出不穷；在游戏引擎里，Slate、UMG、Dear ImGui 又各自为政。

如果你只用"桌面、移动、Web"来分类，会得到一堆互相矛盾的答案：Tauri 算桌面还是 Web？Flutter 算移动还是跨平台？Compose 算 Android 还是桌面？

更有解释力的做法，是把它拆成三条**正交的主线**：

1. **技术实现方式**：原生控件、自绘、Web 壳——决定"像素是怎么来的"。
2. **目标平台**：Windows / macOS / iOS / Linux / Android——决定"像素往哪去"。
3. **语言与生态**：C++ / .NET / Go / Rust / Kotlin / Dart / 游戏引擎——决定"谁来写"。

任何一个 GUI 框架，都可以在这三条轴上各占一个坐标。同一个 Qt，在主线一里是"自绘派"，在主线二里是"全平台覆盖者"，在主线三里是"C++ 的代名词"。三条轴交汇处，就是你项目的最优解。

本文先按三条主线各切一遍，再给出一张横切所有主线的**底层渲染引擎**剖面，最后落到选型决策矩阵。

---

## 主线一：按技术实现方式划分

### 1.1 原生控件派（Native Widgets）

**核心哲学**：系统已经画好了一套漂亮的按钮，我拿来用就行。

每个 UI 控件在操作系统里都对应一个真实的内核对象——Windows 上是 **HWND（窗口句柄）**，macOS 上是 **NSView**，Android 上是 **View**。框架只是这些系统 API 的一层薄薄包装。

**代表**：

- **WinForms**（2002）：Windows 上的经典代表，每个按钮都是一个 HWND，本质是 `user32.dll` / GDI+ 的 C# 包装。界面看起来"土"，但极其稳定、开发极快，在工业软件和内网工具里仍是王者。
- **MFC**：C++ 上的古老 Win32 封装，同源血统。
- **wxWidgets**：C++ 跨平台原生控件派的代表——同一套 API 在 Windows 调 Win32、在 macOS 调 Cocoa、在 Linux 调 GTK，让按钮在每个平台上都是"系统真身"。代表作：**Audacity**（音频编辑器）、**FileZilla**（FTP 客户端）、**KiCad**（电路设计软件）。

**优势**：

- 完美融入系统主题，用户感知最"原生"。
- 资源占用低，对系统辅助功能（无障碍、输入法）支持最好。
- 开发工具链成熟，招人容易。

**天花板**：

- 换主题、做像素级自定义极困难。
- 跨平台基本无望——每个系统一套控件，没法共用代码。
- 动画和现代视觉效果是硬伤。

### 1.2 自绘派（Self-Rendering）

**核心哲学**：只要向系统申请一个空白窗口做"相框"，里面每一个像素都由我自己画。

框架内部维护一棵控件树（Widget Tree），把最终画面通过 2D 图形 API（Direct2D、Skia、OpenGL、Vulkan）绘制出来。即使界面上有一万个按钮，对操作系统来说也**只有一个 HWND**。

**代表**：

- **WPF / WinUI 3**：Windows 上自绘的两代标杆，分别基于 DirectX 和 DComp。
- **Qt（QWidget / Qt Quick）**：跨平台自绘老牌王者。
- **Flutter**：用 Skia/Impeller 像游戏引擎一样直接画 UI。
- **Avalonia**：`.NET` 的"能跑在 Linux 和 Web 的 WPF"。
- **Duilib**：中国开发者的硬核 Windows 自绘框架。
- **Slint / Iced / egui**：Rust 生态的现代自绘三剑客。
- **Fyne / Gio**：纯 Go 的自绘方案。
- **Kotlin Compose Multiplatform**：Jetpack Compose 的跨平台版本。
- **游戏引擎 UI**：UE5 Slate / UMG、Unity UGUI / UI Toolkit。

**子流派**：保留模式 vs 立即模式

| 维度 | 保留模式（WPF/Qt/Flutter/Duilib） | 立即模式（Dear ImGui/egui/Gio） |
|------|--------------------------------|------------------------------|
| 状态管理 | 创建对象保存在内存，调 `setText` 改状态 | 不保存任何状态，每帧重新"画"一遍 |
| 主要目标 | 最终用户 | 开发者 / 游戏内调试工具 |
| 外观定制 | 非常精美，可像素级控制 | 实用主义（灰黑程序员风） |
| 集成难度 | 重型，需要完整事件循环 | 轻量，寄生在任何渲染上下文里 |

**为什么自绘正在成为主流**：

1. 只有自绘才能做到像素级跨平台一致——Flutter 的"一套代码长一样"全靠这个。
2. 硬件加速 + 硬件合成器（DComp、Core Animation）让自绘的性能不再是短板。
3. 系统厂商也在转向自绘——WinUI 3 本身就是微软用 DComp 重画的 Windows 控件。

### 1.3 Web 壳派（WebView / Web Stack）

**核心哲学**：浏览器已经是世界上最强大的自绘 UI 引擎，我直接把它嵌进桌面应用就好。

**代表**：

- **Electron**（老大哥）：自带 Chromium + Node.js。VS Code、Discord、Slack、Figma、Notion 都在用。标准脚手架是 `electron-vite`，采用**双进程模型**——主进程（Node.js）负责系统 API，渲染进程（Chromium）跑 UI，两者通过 **IPC**（`ipcRenderer` / `ipcMain`）通信。
- **Tauri**（Rust 后端挑战者）：抛弃自带 Chromium，改用**系统 WebView**（Windows 的 WebView2、macOS 的 WebKit、Linux 的 WebKitGTK），后端换成 Rust。Tauri 2.0 正式支持 iOS 和 Android。
- **Wails**（Go 后端挑战者）：架构与 Tauri 类似，后端用 Go。
- **PyWebView**（Python 后端）：最简化的 Python 桌面方案。
- **.NET MAUI Blazor Hybrid / Uno Platform Web**：.NET 生态的 Web 目标。

**三者对比**：

| 维度 | Electron | Tauri | Wails |
|------|---------|-------|-------|
| 后端语言 | Node.js | Rust | Go |
| WebView | 自带 Chromium | 系统 WebView | 系统 WebView |
| 空项目体积 | 100 MB+ | 3–10 MB | 10 MB 左右 |
| 闲置内存 | 300 MB+ | 40 MB 左右 | 40 MB 左右 |
| 兼容性 | 完全一致（自带内核） | 受系统 WebView 版本影响 | 受系统 WebView 版本影响 |
| 生态规模 | 超大 | 快速上升 | 中等 |

**代价**：

- 受系统 WebView 版本影响——老版 Windows 上渲染行为可能和最新 Chrome 有差异。
- 前后端之间的 IPC 序列化开销不可忽视。
- 对系统 API 的细节控制不如自绘派。

### 1.4 三派横向对照

| 维度 | 原生控件派 | 自绘派 | Web 壳派 |
|------|-----------|--------|---------|
| HWND 数量 | N 个（每控件一个） | 1 个（只作容器） | 1 个（容纳 WebView） |
| 跨平台能力 | 极差 | 极强 | 极强 |
| 渲染一致性 | 跟随系统 | 像素级可控 | 跟随 WebView |
| 包体积 | 最小 | 中等（5–60 MB） | 大（10–150 MB） |
| 与系统集成度 | 最高 | 中等 | 较低 |
| 动画/现代视觉效果 | 困难 | 强 | 强 |
| 定制自由度 | 低 | 极高 | 极高 |
| 学习曲线 | 平缓 | 陡峭 | 取决于前端背景 |

---

## 主线二：按目标平台划分

### 2.1 Windows：最复杂的"老宅"

在 Windows 生态里，.NET GUI 框架之多常被开发者吐槽为"全家桶"甚至"大乱斗"。之所以会出现这种局面，是因为这 20 多年来 Windows 的硬件环境、交互逻辑以及微软的战略重心发生了数次剧变，而微软为了兼容旧代码又不肯放弃老的框架。

**微软官方框架演化**：

| 代际 | 框架 | 年份 | 渲染引擎 | 现状 |
|------|------|------|---------|------|
| 第一代（古典主义） | WinForms | 2002 | GDI+ | 工业软件、内网工具王者 |
| 第二代（视觉主义） | WPF | 2006 | Direct3D（MIL） | 当前桌面开发事实标准 |
| 第三代尝试 | UWP | 2015 | DComp | 基本失败（过于封闭） |
| 第三代当前 | WinUI 3 / Windows App SDK | 2021 | DComp + Direct3D | 官方推荐"现代 Windows"方案 |
| 第三代多端 | MAUI | 2022 | 多后端 | Windows 上原生感不如 WPF |

**WinUI 3 的杀手锏**：引入 **Windows Composition（Visual Layer）** 和 **DirectComposition（DComp）**，支持毛玻璃、云母效果、子像素级动画。

**社区反超**：微软官方的跨平台故事一直讲不好，反而是社区做出了 **Avalonia** 和 **Uno Platform**，比微软官方更早实现"WPF 式的代码跑在 Linux 和 Web 上"。

**国产硬核流派**：提到 Duilib，就进入了 Windows 桌面开发的一个非常"硬核"且带有鲜明中国特色的领域。早期的**腾讯 QQ、百度杀毒、各种游戏登录器**用的都是它。

- **DirectUI 思想**：整个程序窗口只有一个 HWND，内部所有控件全靠自绘。
- **XML 布局**：率先在 C++ 圈子里大规模推广"用 XML 写界面、用 C++ 写逻辑"的模式，比 WPF 在国内流行还要早。
- **渲染路径**：对 `user32.dll` 的利用非常单纯——申请一个空白窗口，接管 `WM_PAINT`，在内存里画好后一次性 BitBlt 到窗口。
- **体积极小**：编译出来可能只有几百 KB，相比 Qt 的几十 MB 优势明显。

**身世八卦**：Duilib 的鼻祖是丹麦开发者 **Bjarke Viksoe**（2006-2007 年的 DirectUI Demo），真正命名和推广者是中国开发者 **"微蓝"（wielan）**。它**没有固定所属公司**，属于开源社区项目。后来**网易的 nim_duilib** 和腾讯的魔改版接过维护大旗，成为功能最全的分支。

**Windows 专属底层**：DComp（合成器）、DWM（桌面窗口管理器）、DirectWrite（文字渲染）、Direct2D（2D 矢量图）——它们是 WinUI 3 现代视觉效果的底层基石。

**Windows 选型建议**：

| 需求场景 | 推荐框架 | 理由 |
|---------|---------|------|
| 快速做一个内部小工具 | WinForms | 拖拽几分钟搞定，学习成本极低 |
| 主流桌面软件 / 复杂交互 | WPF | 生态最稳，招人容易，性能和颜值平衡最好 |
| 要 Windows 11 原生颜值 | WinUI 3 | 最符合当前系统的视觉规范（圆角、云母效果） |
| 极致轻量 C++ 壳 | Duilib / Slint | 几百 KB 到几 MB，启动飞快 |
| 一套代码跑移动端 + 电脑 | MAUI / Avalonia | 跨平台刚需首选，Avalonia 口碑极佳 |

### 2.2 macOS / iOS：Apple 生态

Apple 对 UI 框架的掌控力极强，且官方方案更迭迅速。

**第一方现代栈**：

- **AppKit**（macOS）：最老牌的 Mac UI 框架，Objective-C 血统，内部对应 NSView。
- **UIKit**（iOS）：iPhone/iPad 的老牌框架，命令式 API。
- **SwiftUI**（2019+）：Apple 的"下一代"声明式 UI 框架，一套代码覆盖 macOS / iOS / watchOS / tvOS / visionOS，基于 Swift 的响应式数据流。在 2026 年已是 Apple 生态新项目的默认选择。
- **Mac Catalyst**：把 iPad App 直接搬到 macOS 的桥接方案。

**第三方跨平台方案在 Apple 上的表现**：

- **Qt**：对 Apple 生态支持完整，但风格偏重，系统集成度一般。
- **Flutter**：通过 Skia 自绘，视觉完全可控，但不太像原生。
- **Tauri**：使用 WKWebView，包体最小。
- **Avalonia / Kotlin CMP**：也能跑，但 App Store 审核和原生感仍是挑战。
- **React Native**：Meta 的老牌方案，桥接到 UIKit，仍被 Instagram、Discord、Coinbase 等使用。

**底层统一**：**Metal** 是 Apple 从 2014 年起力推的 3D/计算统一 API，替代 OpenGL。无论是 SwiftUI、Flutter 还是 Qt Quick，最终在 Apple 平台上都走 Metal。

### 2.3 Linux：最分裂的平台

Linux 桌面没有统一的"官方"UI 框架，长期分裂为两大阵营：

- **GTK**（GNOME 阵营）：C 语言编写，与 GNOME 桌面深度绑定，Firefox、GIMP 在用。
- **Qt / KDE**：C++ 编写，KDE 桌面的底座，应用视觉一致性更好。

**真正跑在 Linux 桌面上的现代框架**：

- **Electron / Tauri**：走 WebKitGTK，是当今 Linux 桌面新应用的主力。
- **Iced**：Rust 写的声明式框架，**System76 的 COSMIC Linux 桌面环境**正是用 Iced 构建的，证明其能支撑完整 DE。
- **Flutter for Linux**：官方支持，但生态远不如桌面那两强。
- **wxWidgets**：Linux 上直接落到 GTK 之上，是 Audacity、FileZilla、KiCad 等跨平台老牌开源软件能同时在 Windows/Mac/Linux 上跑得原生感的关键。
- **JetBrains IDE**：使用自有的 Java Swing 改造栈，不属于以上任何阵营。

**Wayland 时代的变革**：Linux 正在从 X11 迁移到 Wayland——每个 Wayland 合成器（Mutter、KWin、Sway）自带合成能力，传统 X11 时代"窗口管理器 vs 合成器"的分离被终结。对 GUI 框架而言，这意味着对 Wayland 协议的适配正在成为新的门槛。

### 2.4 Android：Compose 统一新原生

Android 平台的 UI 栈正在经历一次彻底的代际更迭：

- **老派**：`View` 体系 + XML 布局（2008 起沿用至今），命令式、基于继承。
- **新派**：**Jetpack Compose**（2021 稳定版），声明式、基于 Kotlin 函数。

**2026 年的现状**：新项目几乎全部选 Jetpack Compose，Google 官方文档也完全倒向它。View 体系还在维护但仅用于老代码。

**跨平台方案在 Android 上**：

- **Flutter**：曾经的跨端王者，仍有闲鱼、字节等厂大规模使用。
- **Kotlin Compose Multiplatform**：从 Android 出发，向桌面和 iOS 扩展，是 Android 开发者最顺手的跨端选择。
- **React Native**：前端团队的选择，仍是 Meta 自家 App 的支柱。
- **Tauri 2.0 Mobile**：基于 WebView 的移动端方案，刚进入生产可用阶段。

### 2.5 真·多平台方案：5 端覆盖度对照

| 框架 | Windows | macOS | Linux | iOS | Android | Web |
|------|:-------:|:-----:|:-----:|:---:|:-------:|:---:|
| **Flutter** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️（SEO 差） |
| **Tauri 2.0** | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| **Kotlin CMP** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️（Alpha） |
| **Avalonia** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅（WASM） |
| **Uno Platform** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MAUI** | ✅ | ✅（Catalyst） | — | ✅ | ✅ | — |
| **Qt** | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| **React Native** | ⚠️ | ⚠️ | — | ✅ | ✅ | ⚠️ |

---

## 主线三：按语言与生态划分

### 3.1 C++ 生态：性能派的主场

C++ 是 GUI 框架最古老、最厚重的生态，代表着对性能和控制力的极致追求。

- **Qt**：老牌王者，跨平台自绘、QWidget + Qt Quick 双路线并存。围绕它形成了完整工具链（Qt Creator、QML Hot Reload、Qt Design Studio）。
- **Duilib 家族**：中国开发者贡献的轻量级 Windows 自绘方案，以 nim_duilib 为代表。
- **Slint**：前 Qt 团队的现代改写，同时提供 Rust 和 **C++** 绑定——对资深 C++ 开发者极为友好，可直接复用现有 C++ 资产。
- **Dear ImGui**：游戏和工具链里的"折叠桌"，极度便携。
- **wxWidgets**：1992 年诞生的老牌跨平台 C++ UI 库，与 Qt 同辈但路线截然相反——Qt 是"自绘派"追求像素一致，wxWidgets 是"原生派"追求"每个平台都长系统该有的样子"。协议使用修改版 LGPL（允许静态链接闭源产品），在商业场景比 Qt 更宽松。代表作：Audacity、FileZilla、KiCad、Code::Blocks IDE。也提供了 **wxPython** 绑定，是 Python 桌面开发中 PyQt/PySide 之外的另一条路。
- **FLTK**：另一个老牌 C++ UI 库，比 wxWidgets 更轻量，但社区已萎缩，仅见于嵌入式和科研软件维护场景。
- **MFC / ATL**：Windows 历史遗产，新项目基本不用。

**PyQt vs PySide：授权引发的商业博弈**

对于想用 Python 写 Qt 应用的开发者，有一个不能回避的现实——**两套绑定，两种协议**，选错了可能要赔上整个项目的商业模式。

| 绑定 | 开发方 | 协议 | 商业影响 |
|------|--------|------|---------|
| **PyQt6** | Riverbank Computing（第三方） | **GPL v3** | 具有传染性：分发给用户即要求整个项目开源，否则必须购买商业授权 |
| **PySide6** | Qt 官方 | **LGPL v3** | 闭源友好：只要**动态链接**（Python 默认就是这种方式），业务代码可以完全闭源 |

PySide 被 Qt 官方收编后，最大的杀手锏就是这个 LGPL 协议——让 Python 开发者可以合法地做闭源商业产品。

### 3.2 C# / .NET 生态：官方臃肿，社区反超

- **官方线**：WinForms → WPF → UWP → WinUI 3 → MAUI，每一代都为了"迎接新时代"而推出，但又不敢抛弃旧框架。
- **社区线**：**Avalonia**（跨平台 WPF）、**Uno Platform**（一套 XAML 跑遍 Windows / Mac / Linux / iOS / Android / Web）反而比官方更早做到真正的跨端。

**为什么社区比官方更早跨平台**：微软受 Windows 商业利益牵制，不愿让 .NET 开发者轻易离开 Windows。而社区没有这个包袱，于是 Avalonia 用 SkiaSharp + 自绘直接给了 `.NET` 一个 Linux 出口。在 2026 年，已有不少 `.NET` 团队把 Avalonia 当作"默认新项目选择"。

### 3.3 Go 生态：纠结但渐进

Go 圈子里对 GUI 一直比较纠结——语言本身很好，但缺少一个 Qt 级别的成熟框架。最大的痛点是 **CGO 调用开销**：每次 Go 调 C 代码涉及栈切换（Go 协程的 2 KB 小栈 vs C 的 8 MB 栈）和调度器脱离，单次开销 50–200ns。这让绑定 GTK/Tk 这类 C 库的方案在 Go 里一直处于边缘地带。

目前比较成熟的选择有三条路线：

**Wails：混合架构的行业明星**

类似 Tauri，但后端用 Go。前端用 Vue/React，利用系统 WebView。是 2026 年 Go 开发者做桌面应用的头号推荐，文档、社区、生产案例都很成熟。优势是把 Go 的并发模型与 Web 生态的 UI 灵活性结合，特别适合做内网工具、管理后台类产品。

**Fyne：纯 Go 的自绘方案**

**Zero CGO**（主核心不需要 CGO），基于 OpenGL/Vulkan 自己渲染 UI，不依赖系统原生组件。最大卖点是可以**静态编译成单一二进制文件**，跨平台分发极简单。代价是 UI 风格偏 Material Design，自定义自由度不如 Web 方案；桌面专属组件（复杂表格、拖拽面板等）积累相比 Qt 还差很远。

**Gio / gioui：即时模式的极致性能**

使用即时模式（IMGUI）思想，纯 Go 实现，帧率极高、内存极低。适合专业工具、监控面板，而不是一般的管理应用。

**绑定 GTK / Tk 在 Go 里黑名单原因**：CGO 开销、交叉编译痛苦、GTK4 绑定（如 `gotk4`）靠自动生成代码非常"不 Go"。除非有历史包袱，否则不建议考虑。

### 3.4 Rust 生态：百花齐放，哲学各异

Rust 的 GUI 生态在 2026 年已从实验室走向工业化，但不同框架在哲学上差异极大。

- **Slint**：前 Qt 团队的现代改写，类 QML 的 `.slint` 描述语言，编译为原生代码。极低内存（<10 MB），可跑在无操作系统的嵌入式单片机上。商业授权比 Qt 宽松很多。
- **Iced**：灵感来自 Elm，完全基于 Rust 的 Ownership 和 Lifetime 重新定义 UI。被用于 System76 的 COSMIC Linux 桌面环境。
- **egui**：即时模式的 Rust 版 ImGui。调试面板、内部工具、游戏内 UI 的首选。
- **Druid / Xilem**：Xilem 是 Druid 的后继，由 Linebender 团队（xi-editor 的作者）打造，目标是做出 Rust 世界的 SwiftUI/Compose。
- **gpui**：Zed 编辑器团队的专用 Rust UI 框架，面向极高刷新率的编辑器场景。

**共同底层**：大多数 Rust GUI 框架最终都走 **wgpu**——Rust 实现的跨平台图形 API，与 W3C 的 WebGPU 标准对齐。

### 3.5 Kotlin 生态：JetBrains 的一体化战略

- **Jetpack Compose**（Android 原生）：Kotlin 声明式 UI 的起点，2021 稳定版。
- **Compose Multiplatform（CMP）**：由 JetBrains 主导，把 Jetpack Compose 扩展到桌面、iOS 和 Web。
  - **渲染**：桌面端用 **Skia** 直接绘图（和 Flutter 走同一条路）。
  - **优势**：Kotlin 语言现代程度高（空安全、协程、模式匹配）；和安卓端可 100% 共享业务代码 + UI；JetBrains IDE 支持达到保姆级。
  - **代价**：依赖裁剪过的 JVM 运行时，**打包体积 40 – 80 MB**，启动速度比 Qt / 纯 C++ 应用慢；桌面专属组件生态远不及 Qt。

JetBrains 在"IDE（IntelliJ 系列）+ 语言（Kotlin）+ 框架（CMP）"三位一体的战略上押注极深，这是 CMP 相对 Flutter 最大的结构性优势——它不是一个孤立的 UI 框架，而是一整套语言生态的延伸。

### 3.6 Dart / Flutter 生态：单框架的荣耀与困境

**Flutter 使用自有的 Skia / Impeller 渲染引擎**，不依赖系统组件，像游戏引擎一样直接在屏幕上画 UI。这带来的最大特性是像素级的跨平台一致性。

**Flutter 在被唱衰吗？** 在 2026 年这是一个有争议的话题。客观来说：它没有死，但确实从"狂热扩张期"进入了"平台期"。

- **真实痛点**：
  - Google 内部 AI 方向（Gemini）抽走了部分资源。
  - Web 端始终是软肋（不仅 SEO 差，文本选择、无障碍等浏览器原生行为都失真）。
  - 对手快速长大：Tauri 2.0 抢轻量桌面市场，Kotlin Compose Multiplatform 抢安卓跨端开发者。
  - **Dart 的孤独**：离开 Flutter，Dart 语言几乎没有大型应用场景。
- **护城河**：
  - 渲染一致性是行业天花板（特别适合高度定制 UI、游戏化产品、金融 App）。
  - Hot Reload 体验仍是跨平台领域的金标准。
  - 底层 C++ 引擎硬核，FFI 调用 C++ 开销远小于 Electron 的 N-API。
  - 生态惯性巨大：从闲鱼、微信支付部分模块到宝马 App，无数生产案例支撑。

**值不值得学？** 取决于场景：移动端优先 + 需要格外精致的 UI 还有 2D 动画 → **值得**；只做桌面、或需要 SEO 的 Web → **避开**。

### 3.7 游戏引擎里的 UI：自成一派的独立生态

游戏引擎的 UI 系统走的是完全不同的路线——它们通常**自带完整的 UI 栈**，不使用操作系统的任何 UI 组件。

**UE5 的三层体系**可以概括为：**以 UMG 为壳，以 Common UI 为交互标准，以 ViewModel 为数据驱动核心**。

1. **Slate**：UE 编辑器界面的底层框架，本质是极致版的自绘框架，逻辑上非常接近 Qt。使用 C++ 宏和运算符重载（`+ SVerticalBox::Slot()`）实现声明式布局。
2. **UMG (Unreal Motion Graphics)**：Slate 之上的包装，"蓝图可视化拖拽 + 属性绑定"逻辑本质上就是 **WinForms 的易用性 + WPF 的数据驱动思想**。
3. **Common UI**：UE5 随 Lyra 示例项目推出的重磅插件，解决了"返回键""手柄/鼠标焦点导航""多层 UI 栈管理"等痛点。引入 **UI Data Tree** 概念。
4. **UMG Viewmodel**：UE5.1 引入的 MVVM 模块。以前 UMG 的属性绑定性能极差（每帧轮询 Tick），现在推崇**事件驱动绑定**——数据改变时通知 ViewModel，再触发 UI 更新。

**UE5 UI 体系对照表**：

| 级别 | UE5 方案 | 对应 .NET/Windows 概念 |
|------|---------|----------------------|
| 视觉层 | UMG + XAML-style logic | WPF |
| 逻辑框架 | Common UI | DWM（窗口管理器） |
| 数据驱动 | UMG Viewmodel | MVVM / 数据绑定 |
| 底层引擎 | Slate | Qt / 自绘引擎 |

**Unity 的双栈**：老栈 **UGUI**（基于 Canvas 的保留模式）+ 新栈 **UI Toolkit**（借鉴 Web 的 UXML/USS 声明式体系）。

**Dear ImGui 为何是游戏工具链标配**：

- **作者**：Omar Cornut（ocornut），由 Dear imgui Team 维护。虽然没有母公司，但暴雪、育碧、卡普空、EA、任天堂都在赞助。
- **极度便携**：只有几个 `.cpp` 和 `.h` 文件，扔进项目就能用。
- **零心智负担**：逻辑变了 UI 自动就变，不需要管"如何更新 UI 状态"。
- **寄生渲染**：对 WinUser 依赖降到绝对零度，只生成顶点数据，寄生在宿主的 DirectX/OpenGL/Vulkan/Metal 上下文里。

游戏开发者通常**不会**用 ImGui 做玩家最终界面（默认长得比较"程序员风"），它的核心舞台是：

- **调试工具**：实时改游戏重力数值、天气、角色坐标。
- **性能分析**：屏幕一角画实时 CPU/GPU 折线图。
- **关卡编辑器**：快速搭建编辑工具。

---

## 横切：底层图形渲染引擎

三条主线切完之后，还有一块公共地基——**底层 2D/3D 渲染引擎**。几乎所有现代自绘型 GUI 框架，最终都会落到这一层。但值得注意的是：**不同的 GUI 框架选择了完全不同的底层**，它们之间是平行的技术路线，而不是依赖关系。

### Skia

Google 的 **2D 图形抽象层**（不是单纯的内存绘图库），支持 Vulkan / Metal / DirectX 12 硬件加速后端。

- **应用**：Chrome 浏览器、Flutter、Android 图形栈、Firefox（部分）、Compose Multiplatform 都以它为基础。
- **特点**：跨平台一致的 2D 绘制 API，支持路径、文字、渐变、阴影。
- **核心抽象**：`SkSurface`（渲染目标）+ `SkCanvas`（绘图接口）解耦，同一套绘图 API 可输出到三种完全不同的后端：

| 模式 | 输出目标 | 典型场景 |
|------|---------|---------|
| **栅格化（CPU）** | 内存 Bitmap、PNG/JPG | 服务端离线渲染、截图 |
| **GPU 加速** | 显卡帧缓冲（Vulkan/Metal/GL/D3D） | UI 框架、实时交互 |
| **矢量输出** | **PDF / SVG 文档** | 报表、打印、矢量导出 |

- **不负责窗口管理**：Skia 能驱动显卡渲染，但不创建窗口。你仍需通过 GLFW、SDL 或原生 Win32/X11/Cocoa 代码获取 `Window Handle`，再交给 Skia 的 `GrDirectContext`。
- **SkSL 跨平台一致性**：Skia 自研的 Shading Language，运行时编译为目标平台 Shader（SPIR-V/MSL/HLSL/GLSL），保证渐变、模糊、混合模式在 iOS 和 Android 上像素级一致。
- **只做 2D**：Skia 的数学模型核心是 2×3 仿射变换（支持 4×4 用于透视变换的 2.5D 视觉欺骗），不包含深度缓冲与真正的 Z 轴投影。它不是 3D 引擎，而是 Cairo、Direct2D、Core Graphics 的同类竞争者。
- **但它依赖 3D API 加速**：Skia 把 2D 路径拆成无数个三角形（Tessellation）扔给 Vulkan/Metal/D3D 并行渲染。所以 Skia 和 GPU 的关系是"工具和目的"：2D 是结果，3D API 是手段。

### Impeller

Flutter 团队为替代 Skia 打造的新一代渲染引擎。

- **目标**：解决 Skia 在首次渲染时的 shader 编译卡顿。
- **策略**：预编译所有 shader，追求可预测的帧率。

### Qt 自有渲染栈（QPainter + Scene Graph / RHI）

Qt **不使用 Skia**，而是从 1990 年代起自己积累了一整套渲染栈。常有人误以为所有跨平台自绘框架都落在 Skia 上，其实 Qt 和 Skia 是**同层级的竞争者**。

Qt 的渲染栈可以分为两条路线：

**① 传统路线（QWidget 体系）：QPainter + Paint Engine**

- `QPainter` 是对开发者暴露的统一绘制 API（类似 Skia 的 `SkCanvas`），本身不干活，真正画图的是底下的 **Paint Engine**。
- Qt 会根据平台自动选择 Paint Engine：
  - **Raster Engine**：默认的 CPU 软件光栅化器，Qt 自己用 C++ 写的（借鉴了 AGG 等思路），包括 Bezier 细分、抗锯齿、路径填充，**与 Skia 没有代码关系**。
  - **OpenGL Engine**：走 OpenGL / OpenGL ES 硬件加速。
  - **CoreGraphics Engine**：macOS 上对接 Apple Quartz。

**② 现代路线（Qt Quick / QML）：Scene Graph + RHI**

- 界面被抽象为一棵 **Scene Graph（场景图）** 节点树，最终转为 GPU 顶点和纹理，更接近游戏引擎的渲染管线。
- Qt 6 引入 **RHI（Rendering Hardware Interface）** 抽象层，把 Scene Graph 对接到 Vulkan / Metal / Direct3D 11/12 / OpenGL，开发者只写一套代码即可跨图形 API 运行。

> **一句话总结**：Skia 是"给别人用的 2D 库"，Qt 的渲染栈是"自产自销的完整 UI 栈"。两者都能画按钮和圆角，但血统不同。

### wgpu

Rust 实现的跨平台图形 API，统一 Vulkan / Metal / DX12 / OpenGL 接口。

- **标准**：与 W3C 的 WebGPU 标准对齐，未来可在浏览器和原生环境共用代码。
- **采用**：Servo、Bevy 游戏引擎、以及多个 Rust GUI 框架都构建在其之上。

### 平台专属合成器

- **DirectComposition（DComp）**：Windows 系统级合成器 API，是 WinUI 3 现代视觉效果（毛玻璃、云母、阴影）的底层。
- **Core Animation**：Apple 平台的层合成 API，与 Metal 深度集成。
- **Wayland Compositor**：Linux 新时代合成器（Mutter、KWin、Sway），接替 X11 的职能。

### 各大框架底层对照表

| 框架 | 2D 渲染层 | GPU 抽象 |
|------|----------|---------|
| **Flutter** | Skia / Impeller | Vulkan / Metal / OpenGL |
| **Chrome** | Skia | ANGLE / Vulkan / Metal |
| **Qt (QWidget)** | 自家 Raster Engine | CPU 光栅化 / OpenGL |
| **Qt Quick** | 自家 Scene Graph | **RHI**（Vulkan / Metal / D3D / GL） |
| **WPF** | Direct2D / MIL | Direct3D |
| **WinUI 3** | Direct2D | DComp + Direct3D |
| **Slint** | 自家渲染器 | wgpu / Skia / 软件 |
| **Kotlin CMP（桌面）** | Skia | OpenGL / Direct3D / Metal |
| **Avalonia** | Skia（SkiaSharp） | 多后端 |
| **SwiftUI** | Core Graphics / Core Animation | Metal |
| **Bevy / Servo** | 自家渲染器 | wgpu |

### 渲染栈的四层分层

一个现代 GUI 栈通常有四层，理解这四层的边界，能帮你判断性能瓶颈到底出在哪里：

1. **窗口与输入层**：HWND / NSWindow / X11 / Wayland Surface，由操作系统提供。
2. **合成层**：DComp / Core Animation / Wayland Compositor，负责最终的屏幕合成。
3. **2D 渲染层**：Skia / Impeller / Direct2D / Qt Raster Engine，负责矢量图形和文字。
4. **UI 框架层**：WPF / Qt / Flutter / Compose，负责控件树、布局和事件分发。

---

## 三维坐标下的选型决策

把三条主线交叉起来，就能得到相当精确的选型建议。下面给出几个典型坐标：

| 语言 ×  平台 × 实现 | 推荐方案 | 理由 |
|---------------------|---------|------|
| **C++ × Windows × 自绘（极轻量）** | Duilib / Slint | 几百 KB 到几 MB，启动飞快 |
| **C++ × 全平台 × 自绘（重型）** | Qt | 生态最完整，工具链最强 |
| **C# × Windows × 原生/半自绘** | WPF（稳） / WinUI 3（现代） | 官方首推 |
| **C# × 全平台 × 自绘** | Avalonia / Uno Platform | 社区比官方更早做到跨端 |
| **Go × 桌面 × Web 壳** | Wails | 2026 年 Go 桌面默认选择 |
| **Go × 桌面 × 自绘** | Fyne | 单二进制分发极简 |
| **Rust × 桌面 × Web 壳** | Tauri | 轻量替代 Electron 的王者 |
| **Rust × 嵌入式/桌面 × 自绘** | Slint / Iced | 前者血统正统，后者 Elm 风 |
| **Kotlin × Android + 跨端 × 自绘** | Compose Multiplatform | JetBrains 一体化生态 |
| **Dart × 移动优先 × 自绘** | Flutter | 像素级一致性的行业天花板 |
| **前端背景 × 全平台 × Web 壳** | Tauri / Electron | 看包体积要求 |
| **Swift × Apple 全家桶 × 原生** | SwiftUI | Apple 官方下一代方案 |
| **游戏工具链 × 立即模式** | Dear ImGui / egui | 几行代码嵌入任何渲染上下文 |
| **游戏成品 UI × 保留模式** | UE5 UMG + Common UI / Unity UI Toolkit | 引擎原生方案 |

---

## 结语：三条主线交汇处的四大趋势

三条正交主线切下来，能看到 2026 年 GUI 世界的四个共同趋势：

1. **主线一方向：自绘吞并一切**。从 WPF 到 Flutter 再到 Tauri，越来越多的框架选择向系统只要一个空白窗口，其余全部自己画——这是唯一能在不同平台上保持一致视觉体验的路线。原生控件派正在退守到"纯 Windows 内部工具"和"Apple 官方生态"两个堡垒。
2. **主线二方向：每个平台都有自己的合成器**。Windows 的 DComp、macOS 的 Core Animation、Linux 的 Wayland Compositor——系统级合成器正在把"窗口管理"从 CPU 剥离到 GPU，让毛玻璃、云母、子像素动画成为标配。
3. **主线三方向：每门现代语言都要有自己的 GUI 原生方案**。Swift 有 SwiftUI、Kotlin 有 Compose、Rust 有 Slint/Iced、Go 有 Fyne/Wails——语言生态已经不满足于"绑定一个 C++ 库"，而是要一套语言原生的声明式 UI。
4. **共同方向：分层解耦越来越清晰**。窗口/合成/2D 渲染/UI 框架四层边界越来越分明，让开发者可以精准地定位性能瓶颈，也让每一层都能独立演化。Skia 能被 Chrome、Flutter、Kotlin CMP、Avalonia 共用，正是这种解耦的成果。

无论你是在维护一个 20 年历史的 WinForms 项目、用 WPF 写商业软件、在 UE5 里做游戏工具，还是用 Tauri 打造新一代桌面应用——把你的项目放进"技术实现 × 目标平台 × 语言生态"的三维坐标系里，大概率能找到已经被别人趟过的那条最佳路径。
