# vibe-writing

AI-friendly Python toolkit for **vibe writing** — fetch, parse, and transform web content into article material.

> *"Vibe writing"*: You describe what you want to write about, AI gathers material and drafts it, you review and refine.

## Features

- 🔍 **Fetch Gemini Conversations** — Retrieve shared Gemini chat pages via headless browser (Playwright), parse Q&A turns into structured data.
- 📝 **Multiple Output Formats** — Export as Markdown text or JSON for downstream AI processing.
- 🛠️ **CLI + Library** — Use from the command line or import in your own scripts / AI agents.

## Quick Start

```bash
# Install with uv
uv sync

# Install browser (first time only)
uv run python -m playwright install chromium

# Fetch a Gemini conversation
uv run fetch-gemini https://gemini.google.com/share/xxx -o output.txt

# Output as JSON
uv run fetch-gemini https://gemini.google.com/share/xxx -f json -o output.json
```

## Library Usage

```python
from vibe_writing import fetch_and_parse, format_as_text

# One-step fetch + parse
turns = fetch_and_parse("https://gemini.google.com/share/xxx")
print(format_as_text(turns))

# Step by step (useful for caching the HTML)
from vibe_writing import fetch_rendered_html, parse_gemini_html

html = fetch_rendered_html(url, wait_seconds=10)
turns = parse_gemini_html(html)
```

## CLI Reference

```
fetch-gemini <url> [options]

Options:
  -o, --output FILE       Output file path (default: stdout)
  -f, --format {text,json} Output format (default: text)
  --wait SECONDS          Wait time for JS rendering (default: 8)
  --save-html FILE        Save rendered HTML for debugging/caching
```

## Project Structure

```
├── src/vibe_writing/       # Python package
│   ├── __init__.py         # Public API exports
│   ├── fetch_gemini.py     # Gemini conversation fetcher & parser
│   └── py.typed            # PEP 561 marker
├── articles/               # Generated articles
├── data/                   # Cached raw data (HTML, text)
├── pyproject.toml          # Project config (uv / hatch)
└── README.md               # This file
```

## Development

```bash
# Create venv and install deps
uv sync

# Run linter
uv run ruff check src/

# Run tests
uv run pytest
```

## License

MIT

---

# vibe-writing（中文说明）

面向 AI 辅助写作的 Python 工具库 —— 抓取、解析、转换网页内容为文章素材。

> *"Vibe writing"（氛围写作）*：你描述想写什么，AI 收集素材并起草，你审阅和润色。

## 功能特性

- 🔍 **抓取 Gemini 对话** —— 通过无头浏览器（Playwright）获取 Gemini 共享聊天页面，将问答轮次解析为结构化数据。
- 📝 **多种输出格式** —— 导出为 Markdown 文本或 JSON，方便下游 AI 处理。
- 🛠️ **命令行 + 库** —— 支持命令行使用，也可在脚本或 AI Agent 中导入调用。

## 快速开始

```bash
# 用 uv 安装依赖
uv sync

# 安装浏览器（仅首次需要）
uv run python -m playwright install chromium

# 抓取 Gemini 对话
uv run fetch-gemini https://gemini.google.com/share/xxx -o output.txt

# 输出为 JSON
uv run fetch-gemini https://gemini.google.com/share/xxx -f json -o output.json
```

## 作为库使用

```python
from vibe_writing import fetch_and_parse, format_as_text

# 一步到位：抓取 + 解析
turns = fetch_and_parse("https://gemini.google.com/share/xxx")
print(format_as_text(turns))

# 分步执行（适合缓存 HTML）
from vibe_writing import fetch_rendered_html, parse_gemini_html

html = fetch_rendered_html(url, wait_seconds=10)
turns = parse_gemini_html(html)
```

## 命令行参考

```
fetch-gemini <url> [选项]

选项：
  -o, --output FILE        输出文件路径（默认：标准输出）
  -f, --format {text,json} 输出格式（默认：text）
  --wait SECONDS           等待 JS 渲染的秒数（默认：8）
  --save-html FILE         同时保存渲染后的 HTML（用于调试/缓存）
```

## 项目结构

```
├── src/vibe_writing/       # Python 包
│   ├── __init__.py         # 公开 API 导出
│   ├── fetch_gemini.py     # Gemini 对话抓取与解析
│   └── py.typed            # PEP 561 类型标记
├── articles/               # 生成的文章
├── data/                   # 缓存的原始数据（HTML、文本）
├── pyproject.toml          # 项目配置（uv / hatch）
└── README.md               # 本文件
```

## 开发

```bash
# 创建虚拟环境并安装依赖
uv sync

# 运行 linter
uv run ruff check src/

# 运行测试
uv run pytest
```

## 许可证

MIT
