"""Market Sub-Agent — 模拟市场数据（Polymarket 需 API Key，此处 mock）"""
import json
import random
import anthropic

# ── 工具实现 ──────────────────────────────────────────────────────────────────

def _fetch_polymarket_volume(topic: str) -> dict:
    """Mock: 模拟 Polymarket 交易量数据"""
    volume = round(random.uniform(10000, 500000), 2)
    liquidity = round(volume * random.uniform(0.3, 0.8), 2)
    return {
        "topic": topic,
        "trading_volume_24h": volume,
        "liquidity": liquidity,
        "active_markets": random.randint(3, 20),
        "trending_markets": [
            {"name": "Will AI pass AGI test by 2025?", "volume": round(random.uniform(5000, 50000), 2)},
            {"name": "OpenAI IPO in 2024?", "volume": round(random.uniform(1000, 30000), 2)},
            {"name": "Claude beats GPT-5?", "volume": round(random.uniform(2000, 40000), 2)},
        ],
        "source": "mock_data",
    }


def _fetch_crypto_price(symbol: str) -> dict:
    """从 CoinGecko 获取加密货币价格（真实数据，无需 API Key）"""
    try:
        import requests
        coin_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
        coin_id = coin_map.get(symbol.upper(), symbol.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if coin_id in data:
            return {
                "symbol": symbol.upper(),
                "price_usd": data[coin_id]["usd"],
                "change_24h": round(data[coin_id].get("usd_24h_change", 0), 2),
            }
        return {"error": f"coin {symbol} not found"}
    except Exception as e:
        return {"error": str(e)}


# ── 工具定义 ──────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "fetch_polymarket_volume",
        "description": "获取 Polymarket 特定主题的交易量和流动性数据（当前为 mock 数据）",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "市场主题，如 AI, crypto"}
            },
            "required": ["topic"],
        },
    },
    {
        "name": "fetch_crypto_price",
        "description": "获取加密货币实时价格（BTC/ETH/SOL）",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "币种符号，如 BTC, ETH, SOL"}
            },
            "required": ["symbol"],
        },
    },
]

TOOL_MAP = {
    "fetch_polymarket_volume": lambda inp: _fetch_polymarket_volume(inp["topic"]),
    "fetch_crypto_price": lambda inp: _fetch_crypto_price(inp["symbol"]),
}


# ── Agent 主函数 ──────────────────────────────────────────────────────────────

async def run_market_agent(client: anthropic.AsyncAnthropic, model: str) -> dict:
    messages = [
        {
            "role": "user",
            "content": (
                "请获取以下市场数据：\n"
                "1. Polymarket AI 主题交易量\n"
                "2. BTC 和 ETH 的实时价格\n\n"
                "最后以 JSON 格式返回，键名：polymarket_volume, polymarket_liquidity, "
                "trending_markets, btc_price, eth_price, btc_change_24h, eth_change_24h"
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
