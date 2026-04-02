"""
Dynamic Dashboard Orchestrator — v1 MVP

并行启动 4 个 Sub-Agent，聚合结果，生成 HTML Dashboard，检查告警。
"""
import asyncio
import traceback
from datetime import datetime

import os
import anthropic
import yaml
from pathlib import Path

from agents.github_agent import run_github_agent
from agents.social_agent import run_social_agent
from agents.market_agent import run_market_agent
from agents.system_agent import run_system_agent
from db import Database
from renderer import render_dashboard
from alerter import check_and_alert

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


async def run_dashboard():
    config = load_config()
    model = config["dashboard"]["model"]
    repo = config["github"]["repo"]
    keyword = repo.split("/")[-1]  # 用 repo 名作社交媒体关键词
    output_file = Path(__file__).parent / config["dashboard"]["output_file"]

    # API Key: 优先 env var，其次 config.yaml
    api_key = os.environ.get("ANTHROPIC_API_KEY") or config.get("anthropic_api_key", "")
    if not api_key:
        raise ValueError(
            "未找到 ANTHROPIC_API_KEY。\n"
            "请设置环境变量：export ANTHROPIC_API_KEY=sk-...\n"
            "或在 config.yaml 中填写 anthropic_api_key 字段。"
        )

    client = anthropic.AsyncAnthropic(api_key=api_key)
    db = Database()

    print(f"\n{'='*60}")
    print(f"  Dynamic Dashboard  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"  监控仓库: {repo}")
    print(f"  模型:     {model}")
    print(f"  并行启动 4 个 Sub-Agent...\n")

    # ── 并行运行 4 个 Sub-Agent ───────────────────────────────────────────────
    tasks = [
        ("github", run_github_agent(client, repo, model)),
        ("social", run_social_agent(client, keyword, model)),
        ("market", run_market_agent(client, model)),
        ("system", run_system_agent(client, model)),
    ]

    results = {}
    async def run_with_label(label, coro):
        print(f"  [{label:8s}] 启动...")
        try:
            data = await coro
            print(f"  [{label:8s}] ✓ 完成")
            return label, data
        except Exception as e:
            print(f"  [{label:8s}] ✗ 失败: {e}")
            traceback.print_exc()
            return label, {"error": str(e)}

    gathered = await asyncio.gather(*[run_with_label(lbl, coro) for lbl, coro in tasks])

    for label, data in gathered:
        results[label] = data
        db.save_metric(label, data)

    # ── 聚合结果 ──────────────────────────────────────────────────────────────
    print(f"\n  聚合结果...")
    metrics = db.get_recent_metrics()

    # ── 生成 HTML ─────────────────────────────────────────────────────────────
    render_dashboard(
        results=results,
        history=metrics,
        config=config,
        output_path=str(output_file),
    )
    print(f"  ✓ Dashboard 已生成: {output_file}")

    # ── 告警检查 ──────────────────────────────────────────────────────────────
    alerts = check_and_alert(results, config, db)
    if alerts:
        print(f"\n  ⚠ 触发告警 {len(alerts)} 条:")
        for a in alerts:
            print(f"    [{a['level']}] {a['message']}")
    else:
        print("  ✓ 无告警")

    print(f"\n{'='*60}\n")
    db.close()
    return results


if __name__ == "__main__":
    asyncio.run(run_dashboard())
