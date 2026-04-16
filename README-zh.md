[English](README.md) | 中文

# vibe-writing

面向 AI 辅助写作的 Python 工具库 —— 抓取、解析、转换网页内容为文章素材。

> *"Vibe writing"（氛围写作）*：你描述想写什么，AI 收集素材并起草，你审阅和润色。

## 功能特性

- 🔍 **统一聊天抓取器** —— 一个 `fetch()` 调用搞定 Gemini、ChatGPT 等平台，自动识别 URL。
- 📝 **多种输出格式** —— 导出为 Markdown 文本或 JSON，方便下游 AI 处理。
- 🛠️ **命令行 + 库** —— 支持命令行使用，也可在脚本或 AI Agent 中导入调用。
- 🤖 **MCP 服务** —— 通过 [Model Context Protocol](https://modelcontextprotocol.io/) 暴露工具，AI 助手可直接调用。
- 📋 **AI Skill** —— 包含 [`SKILL.md`](SKILL.md) 描述文件，AI 助手可自动发现和使用工具。

## 支持的平台

| 平台 | URL 格式 | 状态 |
|------|----------|------|
| Gemini | `gemini.google.com/share/...` / `g.co/gemini/share/...` | ✅ |
| ChatGPT | `chatgpt.com/share/...` / `chat.openai.com/share/...` | ✅ |
| 豆包 (Doubao) | `www.doubao.com/thread/...` | ✅ |

## 快速开始

```bash
# 用 uv 安装依赖
uv sync

# 安装浏览器（仅首次需要）
uv run python -m playwright install chromium

# 抓取任意 AI 聊天分享链接（自动识别平台）
uv run vibe-fetch https://chatgpt.com/share/xxx -o output.txt
uv run vibe-fetch https://gemini.google.com/share/xxx -o output.txt

# 输出为 JSON
uv run vibe-fetch https://chatgpt.com/share/xxx -f json -o output.json
```

## 作为库使用

```python
from vibe_writing import fetch, format_as_text

# 一个调用搞定 —— 自动识别 Gemini、ChatGPT 等
turns = fetch("https://chatgpt.com/share/xxx")
print(format_as_text(turns))

# Gemini 也一样
turns = fetch("https://gemini.google.com/share/xxx")

# 查看支持的平台
from vibe_writing import supported_platforms
print(supported_platforms())
```

### 进阶：使用平台特定的解析器

```python
from vibe_writing import fetch_rendered_html, parse_gemini_html, parse_chatgpt_html, parse_doubao_html

html = fetch_rendered_html(url, wait_seconds=10)
turns = parse_gemini_html(html)   # 或 parse_chatgpt_html(html) / parse_doubao_html(html)
```

## 命令行参考

```
vibe-fetch <url> [选项]

选项：
  -o, --output FILE        输出文件路径（默认：标准输出）
  -f, --format {text,json} 输出格式（默认：text）
  --wait SECONDS           等待 JS 渲染的秒数（默认：8）
  --save-html FILE         同时保存渲染后的 HTML（用于调试/缓存）
```

## MCP 服务

vibe-writing 通过 [MCP（Model Context Protocol）](https://modelcontextprotocol.io/) 暴露工具，
AI 助手（Cursor、Claude Desktop 等）可以直接调用。

### 启动服务

```bash
uv run vibe-mcp
```

### 在 IDE 中配置

添加到 `.cursor/mcp.json`（或等效配置）：

```json
{
  "mcpServers": {
    "vibe-writing": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/vibe-writing", "vibe-mcp"]
    }
  }
}
```

### 可用的 MCP 工具

| 工具 | 说明 |
|------|------|
| `fetch_chat(url, format?, wait?)` | 抓取 AI 聊天分享链接的对话内容 |
| `list_platforms()` | 列出支持的平台和 URL 格式 |

详见 [`SKILL.md`](SKILL.md)。

## 项目结构

```
├── src/vibe_writing/
│   ├── __init__.py          # 公开 API 导出
│   ├── fetch.py             # 统一入口：自动识别 & 分发
│   ├── fetch_gemini.py      # Gemini 对话抓取与解析
│   ├── fetch_chatgpt.py     # ChatGPT 对话抓取与解析
│   ├── fetch_doubao.py      # 豆包对话抓取与解析
│   ├── mcp_server.py        # MCP 服务 —— AI 助手集成
│   ├── _browser.py          # 共享的无头浏览器工具
│   ├── _format.py           # 共享的格式化工具
│   └── py.typed             # PEP 561 类型标记
├── SKILL.md                 # AI Skill 描述文件
├── articles/                # 生成的文章
├── data/                    # 缓存的原始数据
├── pyproject.toml           # 项目配置（uv / hatch）
├── README.md                # English docs
└── README-zh.md             # 中文文档
```

## 开发

```bash
uv sync
uv run ruff check src/
uv run pytest
```

## 许可证

MIT
