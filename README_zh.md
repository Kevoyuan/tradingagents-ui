# TradingAgents UI

一个用于运行 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 分析并阅读报告的本地 Streamlit 桌面式界面。

[English](README.md)

**兼容 TradingAgents v0.3.1**

![TradingAgents UI 实时分析](images/trade-ui-monitor.png)

## 快速开始

需要 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/Kevoyuan/tradingagents-ui.git
cd tradingagents-ui
uv venv --python 3.11
uv pip install -e .
```

### macOS

```bash
./scripts/install-macos-app.sh
open "TradingAgents UI.app"
```

首次设置完成后，直接打开 `TradingAgents UI.app` 即可。

### Windows

双击 `scripts\launch-local-webapp.bat`。启动器会在需要时创建本地环境并在浏览器中打开应用。

## 第一次运行

1. 选择 LLM Provider 和模型。
2. 输入所需的 Provider API Key。
3. 输入 `NVDA` 或 `BTC-USD` 等代码。
4. 选择分析师团队和研究深度。
5. 点击 **Run Analysis**。

实时页面会显示 Agent 进度、工具调用和报告章节。完成后的报告可在 **Browse Reports** 中继续查看。

## 界面截图

### 内嵌 HTML 报告

![内嵌 HTML 报告](images/trade-ui-embedded-html-report.png)

### 报告阅读器

![报告阅读器](images/trade-ui-report-viewer.png)

### 历史报告

![历史报告](images/trade-ui-history-reports.png)

### Provider 配置

![Provider 配置](images/trade-ui-providers.png)

## 核心功能

- 实时多 Agent 分析进度
- 股票与加密货币分析路径
- TradingAgents checkpoint/resume
- 原生及自定义 LLM Provider
- Markdown 与内嵌 HTML 报告
- 本地报告历史和模型专属报告文件
- 可选的本地 API Key 保存

## API Key 与隐私

本地启动器会启用本地模式。保存偏好或运行分析时，API Key 保存在：

```text
~/.tradingagents/.env
```

在系统支持时，该文件仅允许当前用户读取。Key 不会写入本仓库，也不会由 UI 发送到 Streamlit Cloud，只会传给本次运行所选择的 Provider。

直接运行 Streamlit 或部署到 Cloud 时，Key 默认仅在当前会话使用，除非你另外配置平台 Secrets。参见[云端部署](docs/cloud-deployment.md)。

报告保存在：

```text
~/.tradingagents/logs/
```

系统允许创建符号链接时，最新完整报告也会链接到 `~/.tradingagents/latest_report.md`。

## TradingAgents 兼容性

当前版本支持 TradingAgents `>=0.3.1,<0.4`，默认安装精确的 `v0.3.1` tag。应用内更新器也会安装提示中显示的同一个 tag。

Provider 元数据和模型选项会尽量直接复用上游 v0.3.1 registry。仅 UI 专用的兼容端点由本项目单独维护。

## 文档

- [安装与其他启动方式](docs/installation.md)
- [Provider 与凭据](docs/providers.md)
- [云端部署](docs/cloud-deployment.md)
- [局域网访问](docs/lan-access.md)
- [开发说明](docs/development.md)

## 开发

```bash
uv pip install -e .
pytest tests
ruff check .
```

架构、环境变量和 Direct Streamlit 用法见 [docs/development.md](docs/development.md)。
