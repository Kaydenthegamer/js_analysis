# JS 安全漏洞分析 by Gemini AI

这是一个使用 Google Gemini API 对网站的 JavaScript 文件进行安全分析的 Python 工具。它可以帮助开发者和安全研究人员快速识别 JS 代码中潜在的安全漏洞。

## 核心功能

- **URL 分析**: 输入一个网站 URL，工具会自动提取页面中所有的 JavaScript 文件链接。
- **交互式选择**: 在分析前，您可以从提取的 JS 文件列表中选择一个、多个或全部文件进行分析。
- **深度 AI 分析**:
    - **智能分块**: 自动将大型 JS 文件分割成小块，以适应 API 的输入限制。
    - **两阶段总结**: 在对代码块进行初步分析后，会再次调用 AI 对所有分析结果进行最终总结，生成一份全面、连贯的报告。
    - **精确定位**: 最终报告会包含具体的代码片段和行号（如果可用），方便快速定位问题。
- **精美报告**: 分析结果会自动生成为带有 CSS 样式的 HTML 页面，并保存在 `reports/` 目录下，同时自动在浏览器中打开。
- **高度可配置**:
    - **健壮的代理支持**: 支持通过 SOCKS5 代理连接 Gemini API，并默认启用远程DNS解析（`rdns=True`），以确保在各种网络环境下的连接成功率。
    - **完全自定义**: 可以在 `config.ini` 中自定义 API 密钥、模型、代理、分块大小以及用于不同分析阶段的提示词。

## 文件结构

```
.
├── .gitignore          # Git 忽略文件，保护敏感信息和生成的文件
├── config.ini          # 您的个人配置文件 (需要自行创建或从 example 复制)
├── config.ini.example  # 配置文件模板
├── main.py             # 主程序脚本
├── README.md           # 项目说明文件
└── requirements.txt    # Python 依赖库
```

## 安装与设置

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/Xc1Ym/js_analysis
    cd js_analysis
    ```

2.  **安装依赖**:
    建议在 Python 虚拟环境中进行安装。
    ```bash
    pip install -r requirements.txt
    ```

3.  **创建配置文件**:
    复制 `config.ini.example` 文件并将其重命名为 `config.ini`。
    ```bash
    cp config.ini.example config.ini
    ```

4.  **编辑配置文件**:
    打开 `config.ini` 文件，并填入您的个人信息：
    - `api_key`: 您的 Google Gemini API 密钥。
    - `[Proxy]`: 如果您需要通过代理访问 Gemini API，请配置 `type`, `host`, 和 `port`。如果不需要，请将 `type` 留空。

## 使用方法

在项目根目录下运行以下命令：

```bash
python main.py
```

程序将提示您输入要分析的网站 URL。之后，按照屏幕上的指示选择要分析的 JS 文件即可。分析完成后，HTML 报告会自动在您的默认浏览器中打开。

## 配置选项 (`config.ini`)

- **[Gemini]**
    - `api_key`: (必需) 你的 Gemini API 密钥。
    - `model`: 使用的 Gemini 模型，推荐 `gemini-1.5-flash`。
    - `max_chunk_size`: 发送给 API 的单个代码块的最大字符数。

- **[Proxy]**
    - `type`: 代理类型, "http"。如果不需要代理，请留空。
    - `host`: 代理服务器地址。
    - `port`: 代理服务器端口。

- **[Prompt]**
    - `custom_prompt`: 用于分析第一个（或唯一一个）代码块的提示词。
    - `chunk_prompt`: 用于分析后续代码块的提示词。
    - `summary_prompt`: 用于对所有分块分析结果进行最终总结的提示词。
