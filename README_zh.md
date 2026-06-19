# TradingAgents UI

[English](README.md)

给 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 用的本地 Web App。像普通桌面应用一样打开，填参数，跑分析，在同一个窗口里看报告。

![Embedded HTML report](images/trade-ui-embedded-html-report.png)

## 启动方式

只有一个 Streamlit 应用入口：`app.py`。

本地日常使用请通过 `trade-ui` 或仓库自带脚本启动。这些启动器会设置本地模式（`TRADINGAGENTS_UI_LOCAL=1`），因此 API Key 可以保存在这台电脑上，然后再启动 `app.py` 的 Streamlit 服务。

macOS 和 Windows 启动器会先寻找已经能导入 Streamlit 的 Python 环境。如果找不到，会用 `uv` 自动创建 `.venv` 并安装本项目依赖。

也可以直接运行 `streamlit run app.py`。这个方式用于 Streamlit Community Cloud 或高级调试；默认不会把 API Key 保存到本机，除非你自己显式开启本地模式。

### macOS

第一次生成 App：

```bash
./scripts/install-macos-app.sh
```

之后双击：

```text
TradingAgents UI.app
```

它会自动启动本地 Streamlit 服务，并用 Chrome/Edge 的独立 App 窗口打开 `http://localhost:8501`。

`TradingAgents UI.app` 是 macOS 专用。Windows 请用下面的 `.bat` 启动器。

### Windows

第一次安装后，双击这个文件即可启动：

```text
scripts\launch-local-webapp.bat
```

它会在后台启动本地服务，并打开：

```text
http://localhost:8501
```

想更像桌面应用，可以给这个 `.bat` 创建桌面快捷方式。

### 终端启动

```bash
trade-ui
```

本地开发 checkout 可以用等价脚本：

```bash
./run.sh
```

这两个命令都会开启本地模式，并打开同一个 `http://localhost:8501` UI。

### 直接 Streamlit

云端部署或高级调试时使用：

```bash
streamlit run app.py
```

直接 Streamlit 模式下，API Key 只保留在当前会话里。如果你确实想绕过启动器但仍保存本机 API Key，可以这样启动：

```text
# macOS/Linux
TRADINGAGENTS_UI_LOCAL=1 streamlit run app.py

# Windows PowerShell
$env:TRADINGAGENTS_UI_LOCAL="1"; streamlit run app.py
```

## 第一次安装

如果希望桌面启动器自动准备 Python 环境，先安装一次 `uv`：

```text
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
git clone https://github.com/Kevoyuan/tradingagents-ui.git
cd tradingagents-ui
```

然后按你的系统选择启动方式：

- macOS：运行 `./scripts/install-macos-app.sh`，以后双击 `TradingAgents UI.app`
- Windows：双击 `scripts\launch-local-webapp.bat`
- 任意系统终端：运行 `trade-ui`
- 本地开发 checkout：运行 `./run.sh`

终端开发时，也可以手动创建同样的环境：

```bash
uv venv --python 3.11
uv pip install -e .
```

## 使用流程

1. 打开本地 UI
2. 左侧填股票代码、日期、语言、分析团队、模型和 API Key
3. 点击 **Run Analysis**
4. 分析完成后打开 **Browse Reports**
5. 默认直接在页面里看 HTML 报告，也可以切换回 Markdown

API Key 会保存在本机，下次打开自动加载。云端部署时不会保存用户 API Key。

## 内置 TradingAgents 更新检查

软件打开时会在后台静默检查一次 GitHub。

启动命令不会在打开 UI 前更新 TradingAgents。更新统一在 UI 内处理，这样所有本地启动器行为一致。

如果发现 TradingAgents 有更新，左上角侧边栏的 **TradingAgents** LOGO 旁边会出现一个更新图标。没有更新时，这个图标不会出现。

需要更新时，点击这个图标即可从 GitHub 安装或更新 TradingAgents。更新后建议重启应用，确保已经加载的 Python 模块刷新干净。

## 报告体验

Browse Reports 默认展示内嵌 HTML 报告，不再需要弹出外部浏览器窗口。

内嵌 HTML 渲染只在本机处理已保存的 Markdown 报告，不会调用 LLM，也不会消耗 API token。

你可以：

- 在同一行选择报告、切换 HTML/Markdown、复制 Markdown
- 用报告左侧目录跳到章节
- 用右侧 Top/Bottom 按钮快速到顶部或底部
- 在深色 Quant Terminal 主题里阅读长报告

历史报告保存在：

```text
~/.tradingagents/logs/.../reports/
```

## 手机访问

电脑和手机在同一个 Wi-Fi 下时：

```bash
trade-ui --lan
```

或者：

```bash
./run-lan.sh
```

终端会打印类似：

```text
http://192.168.1.23:8501
```

在手机浏览器打开这个地址即可。报告仍然保存在电脑上，手机只是访问正在运行的本地 Web App。

## 云端部署

想不用保持电脑在线，可以部署到 Streamlit Community Cloud：

1. 把 repo 推到 GitHub
2. 在 Streamlit Community Cloud 新建 app
3. Main file path 填 `app.py`
4. Python 使用 3.10 或更新
5. 不要把 API Key 写进 Secrets 或代码
6. 部署后打开生成的 URL

Cloud 注意事项：

- 每个用户在侧边栏输入自己的 API Key
- 云端直接运行 `app.py`，不要使用本地 `trade-ui` 启动器
- Cloud 报告保存在云端容器内，适合临时查看
- Ollama、localhost LiteLLM 这类本地服务不能直接被云端访问

## 功能概览

- 本地一键启动
- macOS 独立窗口 App
- Windows 双击脚本
- 侧边栏配置股票、日期、语言、分析团队、模型和 API Key
- 内置 TradingAgents GitHub 更新检查
- 实时查看 agent 进度、消息、工具调用、token 和耗时
- 历史报告内嵌 HTML 查看
- Markdown 一键复制
- HTML/Markdown 视图切换
- 报告目录、Top/Bottom 快速导航
- 本地保存偏好设置和 API Key
- 支持同 Wi-Fi 手机访问

## 其他截图

### Live Analysis Monitor

![Live analysis monitor](images/trade-ui-monitor.png)

### Report Viewer

![Report viewer](images/trade-ui-report-viewer.png)

### Report History

![Report history](images/trade-ui-history-reports.png)

## 开发者说明

UI 入口始终是 `app.py`。

本地启动器包括 `trade-ui`、`python -m trade_ui.cli`、`./run.sh`、`./run-lan.sh` 以及 macOS/Windows 启动脚本。它们会解析 app 路径，设置 `TRADINGAGENTS_UI_LOCAL=1`，然后执行 Streamlit。

macOS 和 Windows 启动脚本会优先使用 `.venv`，再寻找其他能导入 Streamlit 的 Python。如果都不可用且已经安装 `uv`，它们会自动执行 `uv venv --python 3.11 .venv` 和 `uv pip install -e .`。可以用 `TRADINGAGENTS_UI_PYTHON_VERSION` 覆盖默认 Python 版本。

本地启动器的 app 路径优先级：

1. `TRADINGAGENTS_UI_APP_PATH`
2. 当前目录下的 `./app.py`
3. 已安装包里的 fallback `app.py`

直接 `streamlit run app.py` 会绕过启动器。它适合 Streamlit Cloud 和调试，但除非设置 `TRADINGAGENTS_UI_LOCAL=1`，否则 API Key 只在会话内保存。

TradingAgents 更新检查在 `app.py` 里，由侧边栏更新图标触发。CLI 启动时不会安装或更新 TradingAgents。

如果你在开发本地 TradingAgents checkout：

```bash
export TRADINGAGENTS_DIR=/path/to/tradingagents
```

项目结构：

```text
tradingagents-ui/
├── app.py
├── ui_config.py
├── ui_styles.py
├── ui_panels.py
├── preferences.py
├── scripts/
│   ├── install-macos-app.sh
│   ├── launch-local-webapp.sh
│   └── launch-local-webapp.bat
├── tools/
│   └── baoyu-markdown-to-html/
├── trade_ui/
│   └── cli.py
├── pyproject.toml
├── run.sh
└── run-lan.sh
```
