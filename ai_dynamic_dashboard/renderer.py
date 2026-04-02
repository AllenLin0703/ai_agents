"""HTML Dashboard 渲染器 — 生成自包含的静态 HTML 文件"""
import json
from datetime import datetime
from pathlib import Path


def _gauge(value: float, max_val: float = 100, warn: float = 70, crit: float = 90) -> str:
    """生成进度条 HTML"""
    pct = min(100, round(value / max_val * 100))
    color = "#e74c3c" if value >= crit else "#f39c12" if value >= warn else "#2ecc71"
    return (
        f'<div class="gauge-wrap">'
        f'<div class="gauge-bar" style="width:{pct}%;background:{color}"></div>'
        f'</div>'
        f'<span class="gauge-val" style="color:{color}">{value:.1f}%</span>'
    )


def _card(title: str, icon: str, content: str, badge: str = "") -> str:
    badge_html = f'<span class="badge">{badge}</span>' if badge else ""
    return f"""
    <div class="card">
      <div class="card-header">
        <span class="card-icon">{icon}</span>
        <h3>{title}</h3>
        {badge_html}
      </div>
      <div class="card-body">{content}</div>
    </div>"""


def _stat(label: str, value, unit: str = "") -> str:
    return f'<div class="stat"><span class="stat-val">{value}</span><span class="stat-lbl">{label}{(" " + unit) if unit else ""}</span></div>'


def _render_github(data: dict, repo: str) -> str:
    if "error" in data:
        return f'<p class="error">获取失败: {data["error"]}</p>'

    stats = f"""
    <div class="stat-grid">
      {_stat("⭐ Stars", f"{data.get('stars', 0):,}")}
      {_stat("🍴 Forks", f"{data.get('forks', 0):,}")}
      {_stat("🐛 Issues", f"{data.get('open_issues', 0):,}")}
      {_stat("👁 Watchers", f"{data.get('watchers', 0):,}")}
    </div>"""

    commits = data.get("recent_commits", [])
    commit_html = ""
    if commits:
        rows = "".join(
            f'<tr><td class="sha">{c.get("sha","")}</td>'
            f'<td class="msg">{c.get("message","")[:60]}</td>'
            f'<td class="author">{c.get("author","")}</td></tr>'
            for c in commits[:5]
        )
        commit_html = f"""
        <div class="section-title">最近 Commits</div>
        <table class="commit-table"><thead>
          <tr><th>SHA</th><th>信息</th><th>作者</th></tr>
        </thead><tbody>{rows}</tbody></table>"""

    link = f'<a class="repo-link" href="https://github.com/{repo}" target="_blank">🔗 {repo}</a>'
    return stats + link + commit_html


def _render_social(data: dict) -> str:
    if "error" in data:
        return f'<p class="error">获取失败: {data["error"]}</p>'

    mentions = data.get("twitter_mentions", data.get("mentions_last_24h", "N/A"))
    sentiment = data.get("sentiment", {})
    pos = int(sentiment.get("positive", 0)) if isinstance(sentiment, dict) else 0
    neg = int(sentiment.get("negative", 0)) if isinstance(sentiment, dict) else 0
    neu = max(0, 100 - pos - neg)

    stories = data.get("top_stories", data.get("hacker_news_results", {}).get("top_stories", []))
    stories_html = ""
    if stories:
        items = "".join(
            f'<li><a href="{s.get("url","#")}" target="_blank">{s.get("title","")}</a>'
            f' <span class="points">▲{s.get("points",0)}</span></li>'
            for s in stories[:4]
        )
        stories_html = f'<div class="section-title">HN 热点</div><ul class="story-list">{items}</ul>'

    return f"""
    <div class="stat-grid">
      {_stat("📢 Twitter提及(24h)", mentions)}
      {_stat("😊 正面情感", f"{pos}%")}
      {_stat("😠 负面情感", f"{neg}%")}
      {_stat("😐 中性情感", f"{neu}%")}
    </div>
    <div class="sentiment-bar">
      <div style="width:{pos}%;background:#2ecc71;height:8px;border-radius:4px 0 0 4px;display:inline-block"></div>
      <div style="width:{neu}%;background:#95a5a6;height:8px;display:inline-block"></div>
      <div style="width:{neg}%;background:#e74c3c;height:8px;border-radius:0 4px 4px 0;display:inline-block"></div>
    </div>
    {stories_html}"""


def _render_market(data: dict) -> str:
    if "error" in data:
        return f'<p class="error">获取失败: {data["error"]}</p>'

    vol = data.get("polymarket_volume", 0)
    liq = data.get("polymarket_liquidity", 0)
    btc = data.get("btc_price", "N/A")
    eth = data.get("eth_price", "N/A")
    btc_ch = data.get("btc_change_24h", 0)
    eth_ch = data.get("eth_change_24h", 0)

    def price_color(ch):
        try:
            return "#2ecc71" if float(ch) >= 0 else "#e74c3c"
        except (TypeError, ValueError):
            return "#95a5a6"

    def fmt_change(ch):
        try:
            v = float(ch)
            return f"{'▲' if v >= 0 else '▼'}{abs(v):.2f}%"
        except (TypeError, ValueError):
            return "N/A"

    def fmt_price(p):
        try:
            return f"${float(p):,.2f}"
        except (TypeError, ValueError):
            return str(p)

    def fmt_usd(v):
        try:
            return f"${float(v):,.0f}"
        except (TypeError, ValueError):
            return str(v)

    markets = data.get("trending_markets", [])
    markets_html = ""
    if markets:
        rows = "".join(
            f'<tr><td>{m.get("name","")[:50]}</td><td>{fmt_usd(m.get("volume",0))}</td></tr>'
            for m in markets[:3]
        )
        markets_html = (
            '<div class="section-title">热门预测市场</div>'
            '<table class="commit-table"><thead><tr><th>市场</th><th>交易量</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )

    btc_color = price_color(btc_ch)
    eth_color = price_color(eth_ch)
    btc_change_str = fmt_change(btc_ch)
    eth_change_str = fmt_change(eth_ch)

    return (
        f'<div class="stat-grid">'
        f'{_stat("📈 Polymarket(24h)", fmt_usd(vol))}'
        f'{_stat("💧 流动性", fmt_usd(liq))}'
        f'<div class="stat"><span class="stat-val">{fmt_price(btc)}</span>'
        f'<span class="stat-lbl">BTC <span style="color:{btc_color}">{btc_change_str}</span></span></div>'
        f'<div class="stat"><span class="stat-val">{fmt_price(eth)}</span>'
        f'<span class="stat-lbl">ETH <span style="color:{eth_color}">{eth_change_str}</span></span></div>'
        f'</div>{markets_html}'
    )


def _render_system(data: dict) -> str:
    if "error" in data:
        return f'<p class="error">获取失败: {data["error"]}</p>'

    cpu = data.get("cpu_percent", 0)
    mem = data.get("memory_percent", 0)
    disk = data.get("disk_percent", 0)
    mem_used = data.get("memory_used_gb", data.get("used_gb", 0))
    mem_total = data.get("memory_total_gb", data.get("total_gb", 0))
    disk_used = data.get("disk_used_gb", 0)
    disk_total = data.get("disk_total_gb", 0)
    conns = data.get("active_connections", 0)
    load = data.get("load_avg_1m", "N/A")

    return f"""
    <div class="sys-metrics">
      <div class="sys-row">
        <span class="sys-label">CPU</span>
        {_gauge(cpu, warn=70, crit=90)}
      </div>
      <div class="sys-row">
        <span class="sys-label">内存</span>
        {_gauge(mem, warn=75, crit=85)}
        <span class="sys-detail">{mem_used}/{mem_total} GB</span>
      </div>
      <div class="sys-row">
        <span class="sys-label">磁盘</span>
        {_gauge(disk, warn=80, crit=90)}
        <span class="sys-detail">{disk_used}/{disk_total} GB</span>
      </div>
    </div>
    <div class="stat-grid" style="margin-top:12px">
      {_stat("🔗 活跃连接", conns)}
      {_stat("📊 负载均值(1m)", load)}
      {_stat("🖥 CPU核心", data.get("cpu_count", "N/A"))}
    </div>"""


CSS = """
:root {
  --bg: #0f1117;
  --card: #1a1d27;
  --border: #2a2d3a;
  --text: #e2e8f0;
  --muted: #718096;
  --accent: #667eea;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  padding: 24px;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
header h1 { font-size: 22px; font-weight: 700; color: var(--accent); }
.ts { color: var(--muted); font-size: 12px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(440px, 1fr)); gap: 20px; }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(102,126,234,0.08);
  border-bottom: 1px solid var(--border);
}
.card-icon { font-size: 20px; }
.card-header h3 { font-size: 15px; font-weight: 600; flex: 1; }
.badge {
  background: var(--accent);
  color: white;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 11px;
}
.card-body { padding: 16px 18px; }
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.stat {
  background: rgba(255,255,255,0.04);
  border-radius: 8px;
  padding: 10px;
  text-align: center;
}
.stat-val { display: block; font-size: 18px; font-weight: 700; color: var(--accent); }
.stat-lbl { display: block; font-size: 11px; color: var(--muted); margin-top: 4px; }
.gauge-wrap {
  flex: 1;
  height: 10px;
  background: rgba(255,255,255,0.08);
  border-radius: 5px;
  overflow: hidden;
  display: inline-block;
  width: 60%;
  vertical-align: middle;
}
.gauge-bar { height: 100%; border-radius: 5px; transition: width .3s; }
.gauge-val { margin-left: 8px; font-weight: 600; font-size: 13px; }
.sys-metrics { display: flex; flex-direction: column; gap: 10px; }
.sys-row { display: flex; align-items: center; gap: 10px; }
.sys-label { width: 44px; color: var(--muted); font-size: 12px; }
.sys-detail { color: var(--muted); font-size: 11px; margin-left: 6px; }
.section-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--muted);
  margin: 14px 0 8px;
}
.commit-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.commit-table th { color: var(--muted); text-align: left; padding: 4px 6px; }
.commit-table td { padding: 5px 6px; border-top: 1px solid var(--border); }
.sha { font-family: monospace; color: var(--accent); width: 52px; }
.msg { color: var(--text); }
.author { color: var(--muted); width: 90px; }
.points { color: #f39c12; font-size: 11px; margin-left: 6px; }
.story-list { list-style: none; }
.story-list li { padding: 5px 0; border-top: 1px solid var(--border); }
.story-list a { color: var(--text); text-decoration: none; }
.story-list a:hover { color: var(--accent); }
.sentiment-bar { height: 8px; width: 100%; display: flex; margin: 8px 0 14px; }
.repo-link {
  display: inline-block;
  color: var(--accent);
  text-decoration: none;
  font-size: 12px;
  margin-bottom: 12px;
}
.error { color: #e74c3c; font-size: 13px; }
footer { margin-top: 32px; text-align: center; color: var(--muted); font-size: 12px; }
"""


def render_dashboard(results: dict, history: dict, config: dict, output_path: str):
    repo = config["github"]["repo"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    github_html = _render_github(results.get("github", {}), repo)
    social_html = _render_social(results.get("social", {}))
    market_html = _render_market(results.get("market", {}))
    system_html = _render_system(results.get("system", {}))

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{config['dashboard'].get('refresh_interval_seconds', 300)}">
<title>Dynamic Dashboard — {repo}</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>⚡ Dynamic Dashboard</h1>
  <span class="ts">最后更新: {now} &nbsp;|&nbsp; 自动刷新: {config['dashboard'].get('refresh_interval_seconds', 300)}s</span>
</header>
<div class="grid">
  {_card("GitHub", "🐙", github_html, repo)}
  {_card("社交媒体", "📣", social_html, "Twitter + HN")}
  {_card("市场数据", "📊", market_html, "Polymarket + Crypto")}
  {_card("系统健康", "💻", system_html, "Real-time")}
</div>
<footer>
  Powered by Claude Sub-Agents &nbsp;•&nbsp;
  github={repo} &nbsp;•&nbsp;
  model={config['dashboard']['model']}
</footer>
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")
