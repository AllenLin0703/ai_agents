"""告警模块 — 检查阈值，触发 Discord Webhook"""
import json
import requests
from datetime import datetime


def _send_discord(webhook_url: str, message: str, level: str):
    """发送 Discord 消息"""
    color = {"INFO": 0x3498DB, "WARNING": 0xF39C12, "CRITICAL": 0xE74C3C}.get(level, 0x95A5A6)
    payload = {
        "embeds": [{
            "title": f"{'⚠️' if level == 'WARNING' else '🚨' if level == 'CRITICAL' else 'ℹ️'} Dashboard 告警",
            "description": message,
            "color": color,
            "footer": {"text": f"Dynamic Dashboard • {datetime.now().strftime('%H:%M:%S')}"},
        }]
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Discord 发送失败: {e}")


def check_and_alert(results: dict, config: dict, db) -> list:
    """
    检查所有指标是否超过阈值。
    返回触发的告警列表。
    """
    triggered = []
    thresholds = config.get("alerts", {})
    webhook_url = config.get("discord", {}).get("webhook_url", "")

    def alert(level: str, message: str):
        triggered.append({"level": level, "message": message})
        db.save_alert(level, message)
        if webhook_url:
            _send_discord(webhook_url, message, level)

    # ── 系统健康告警 ──────────────────────────────────────────────────────────
    system = results.get("system", {})
    cpu = system.get("cpu_percent")
    if cpu is not None and cpu > thresholds.get("cpu_percent", 90):
        alert("CRITICAL", f"CPU 使用率过高：{cpu}%（阈值 {thresholds.get('cpu_percent', 90)}%）")

    mem = system.get("memory_percent")
    if mem is not None and mem > thresholds.get("memory_percent", 85):
        alert("WARNING", f"内存使用率过高：{mem}%（阈值 {thresholds.get('memory_percent', 85)}%）")

    disk = system.get("disk_percent")
    if disk is not None and disk > 90:
        alert("WARNING", f"磁盘使用率过高：{disk}%")

    # ── GitHub 告警（需历史数据对比） ─────────────────────────────────────────
    github = results.get("github", {})
    stars = github.get("stars")
    if stars is not None:
        # 简单示例：如果 stars > 100k 触发一条庆祝信息
        if stars > 100_000:
            alert("INFO", f"🎉 {config['github']['repo']} 已达到 {stars:,} stars！")

    # ── 社交情感告警 ──────────────────────────────────────────────────────────
    social = results.get("social", {})
    sentiment = social.get("sentiment", {})
    if isinstance(sentiment, dict):
        neg = sentiment.get("negative", 0)
        if neg > 30:
            alert("WARNING", f"负面情感比例过高：{neg}%")

    return triggered
