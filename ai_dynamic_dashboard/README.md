# ⚡ Dynamic Dashboard — AI Multi-Agent 实时监控面板

> 用 **Claude Sub-Agent** 并行抓取 GitHub / 社交媒体 / 市场数据 / 系统健康，自动生成一张实时 HTML Dashboard。

![Dashboard Preview](https://img.shields.io/badge/status-v1%20MVP-brightgreen) ![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Claude](https://img.shields.io/badge/powered%20by-Claude%20Opus%204.6-purple)

---

## 📺 效果预览

| 模块 | 数据来源 | 是否真实 |
|------|---------|---------|
| 🐙 GitHub | GitHub REST API | ✅ 真实 |
| 📣 社交媒体 | HN Algolia API + Twitter Mock | ⚡ 混合 |
| 📊 市场数据 | CoinGecko API + Polymarket Mock | ⚡ 混合 |
| 💻 系统健康 | psutil 本地读取 | ✅ 真实 |

---

## 🏗 架构原理

```
python3 orchestrator.py
        │
        ├── asyncio.gather() 并行启动 4 个 Sub-Agent
        │
        ├── [GitHub Agent]   Claude 调工具 → GitHub API → 返回 JSON
        ├── [Social Agent]   Claude 调工具 → HN API + Mock → 返回 JSON
        ├── [Market Agent]   Claude 调工具 → CoinGecko + Mock → 返回 JSON
        └── [System Agent]   Claude 调工具 → psutil → 返回 JSON
                │
                ▼
        SQLite 存储历史数据 (dashboard.db)
                │
                ▼
        渲染 dashboard.html（暗色主题）
                │
                ▼
        检查告警阈值 → Discord Webhook（可选）
```

每个 Sub-Agent 都是一个完整的 **LLM Agentic Loop**：Claude 自主决定调用哪些工具、按什么顺序，最终返回结构化 JSON。

---

## 📁 项目结构

```
ai_dynamic_dashboard/
├── orchestrator.py        # 主入口：并行调度所有 Sub-Agent
├── config.yaml            # 配置文件（仓库名 / 告警阈值 / Discord）
├── db.py                  # SQLite 存储层（metrics + alerts 两张表）
├── renderer.py            # HTML 渲染器（暗色主题，自动刷新）
├── alerter.py             # 告警模块（阈值检查 + Discord Webhook）
├── requirements.txt       # Python 依赖
├── agents/
│   ├── github_agent.py    # GitHub Sub-Agent
│   ├── social_agent.py    # Social Sub-Agent（HN 真实 + Twitter Mock）
│   ├── market_agent.py    # Market Sub-Agent（CoinGecko 真实 + Polymarket Mock）
│   └── system_agent.py    # System Sub-Agent（psutil 实时系统数据）
├── dashboard.html         # 生成的 Dashboard（运行后产生）
└── dashboard.db           # SQLite 历史数据库（运行后产生）
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`：

```yaml
anthropic_api_key: "sk-..."   # 或用环境变量 ANTHROPIC_API_KEY

github:
  repo: "anthropics/claude-code"   # 你想监控的 GitHub 仓库

alerts:
  github_stars_per_hour: 50
  cpu_percent: 90
  memory_percent: 85

discord:
  webhook_url: ""   # 填入 Discord Webhook URL（为空则跳过）
```

### 3. 运行

```bash
# 方式一：使用环境变量（推荐）
export ANTHROPIC_API_KEY=sk-...
python3 orchestrator.py

# 方式二：在 config.yaml 中填写 api_key
python3 orchestrator.py
```

### 4. 查看 Dashboard

运行完成后，用浏览器打开 `dashboard.html`：

```bash
open dashboard.html   # macOS
```

---

## ⚙️ 配置说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `github.repo` | 监控的 GitHub 仓库 | `anthropics/claude-code` |
| `alerts.cpu_percent` | CPU 告警阈值 | `90` |
| `alerts.memory_percent` | 内存告警阈值 | `85` |
| `discord.webhook_url` | Discord 通知 Webhook | 空（不发送） |
| `dashboard.model` | 使用的 Claude 模型 | `claude-opus-4-6` |

---

## 🤖 Sub-Agent 详解

### GitHub Agent
- 工具：`fetch_github_repo` / `fetch_github_commits`
- 数据：Stars、Forks、Open Issues、Watchers、最近 Commits
- API：`api.github.com`（无需认证，公开仓库）

### Social Agent
- 工具：`fetch_twitter_mentions`（Mock）/ `fetch_hacker_news`（真实）
- 数据：Twitter 提及量、情感分析、HN 热门讨论
- API：`hn.algolia.com`

### Market Agent
- 工具：`fetch_polymarket_volume`（Mock）/ `fetch_crypto_price`（真实）
- 数据：BTC/ETH 实时价格及 24h 涨跌、Polymarket 预测市场
- API：`api.coingecko.com`（无需 API Key）

### System Agent
- 工具：`get_cpu_metrics` / `get_memory_metrics` / `get_disk_metrics` / `get_network_metrics`
- 数据：CPU 使用率、内存、磁盘、网络 IO
- 库：`psutil`（跨平台）

---

## 🗺 后续迭代计划

| 版本 | 功能 |
|------|------|
| v1 MVP | 4 个并行 Sub-Agent + HTML Dashboard + Discord 告警 ✅ |
| v2 | 趋势分析 + 根因推断 + 熔断/降级机制 |
| v3 | FastAPI + WebSocket 实时推送 |
| v4 | YAML 自然语言配置 + 动态 Agent 生成 |

---

## 📦 依赖

```
anthropic>=0.40.0   # Claude API SDK
psutil>=5.9.0       # 系统指标
requests>=2.31.0    # HTTP 请求
pyyaml>=6.0         # 配置文件解析
```

---

## 📄 License

MIT

---

> Built with [Claude Opus 4.6](https://anthropic.com) · Powered by Multi-Agent Architecture
