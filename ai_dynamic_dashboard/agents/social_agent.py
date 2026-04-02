"""Social Sub-Agent — 模拟社交媒体数据（Twitter/X 需付费 API，此处 mock）"""
import json
import random
import anthropic

# ── 工具实现 ──────────────────────────────────────────────────────────────────

def _fetch_twitter_mentions(keyword: str) -> dict:
    """Mock: 模拟 Twitter mention 数据（真实环境替换为 Twitter API v2）"""
    base = random.randint(50, 300)
    sentiment_pos = random.randint(40, 75)
    sentiment_neg = random.randint(5, 20)
    sentiment_neu = 100 - sentiment_pos - sentiment_neg
    return {
        "keyword": keyword,
        "mentions_last_24h": base,
        "sentiment": {
            "positive": sentiment_pos,
            "negative": sentiment_neg,
            "neutral": sentiment_neu,
        },
        "top_topics": ["AI", "coding assistant", "open source", "developer tools"],
        "source": "mock_data",
    }


def _fetch_hacker_news(keyword: str) -> dict:
    """查询 Hacker News Algolia API（真实数据）"""
    try:
        import requests
        url = f"https://hn.algolia.com/api/v1/search?query={keyword}&numericFilters=created_at_i>0&hitsPerPage=5"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])
        return {
            "keyword": keyword,
            "total_results": data.get("nbHits", 0),
            "top_stories": [
                {
                    "title": h.get("title", ""),
                    "points": h.get("points", 0),
                    "url": h.get("url", ""),
                }
                for h in hits[:5]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


# ── 工具定义 ──────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "fetch_twitter_mentions",
        "description": "获取关键词在 Twitter 的提及次数和情感分析（当前为 mock 数据）",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "要追踪的关键词，如 claude-code"}
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "fetch_hacker_news",
        "description": "从 Hacker News 获取关键词相关的热门讨论",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["keyword"],
        },
    },
]

TOOL_MAP = {
    "fetch_twitter_mentions": lambda inp: _fetch_twitter_mentions(inp["keyword"]),
    "fetch_hacker_news": lambda inp: _fetch_hacker_news(inp["keyword"]),
}


# ── Agent 主函数 ──────────────────────────────────────────────────────────────

async def run_social_agent(client: anthropic.AsyncAnthropic, keyword: str, model: str) -> dict:
    messages = [
        {
            "role": "user",
            "content": (
                f"请获取关键词 `{keyword}` 的社交媒体数据：\n"
                "1. Twitter 提及量和情感分析\n"
                "2. Hacker News 相关讨论\n\n"
                "最后以 JSON 格式返回，键名：twitter_mentions, sentiment, hacker_news_results, top_stories"
            ),
        }
    ]

    while True:
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    text = block.text.strip()
                    try:
                        start = text.index("{")
                        end = text.rindex("}") + 1
                        return json.loads(text[start:end])
                    except (ValueError, json.JSONDecodeError):
                        return {"raw": text}
            return {}

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = TOOL_MAP[block.name](block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    return {}
