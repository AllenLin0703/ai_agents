"""GitHub Sub-Agent — 通过工具调用获取 GitHub 仓库指标"""
import json
import requests
import anthropic

# ── 工具实现 ──────────────────────────────────────────────────────────────────

def _fetch_github_repo(repo: str) -> dict:
    """调用 GitHub REST API 获取仓库基础信息"""
    url = f"https://api.github.com/repos/{repo}"
    headers = {"Accept": "application/vnd.github+json"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        d = resp.json()
        return {
            "stars": d.get("stargazers_count", 0),
            "forks": d.get("forks_count", 0),
            "open_issues": d.get("open_issues_count", 0),
            "watchers": d.get("subscribers_count", 0),
            "description": d.get("description", ""),
        }
    except Exception as e:
        return {"error": str(e)}


def _fetch_github_commits(repo: str) -> dict:
    """获取最近 10 条 commit 信息"""
    url = f"https://api.github.com/repos/{repo}/commits?per_page=10"
    headers = {"Accept": "application/vnd.github+json"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        commits = resp.json()
        return {
            "recent_commits": [
                {
                    "sha": c["sha"][:7],
                    "message": c["commit"]["message"].split("\n")[0][:80],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"],
                }
                for c in commits
            ]
        }
    except Exception as e:
        return {"error": str(e)}


# ── 工具定义（传给 Claude）────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "fetch_github_repo",
        "description": "获取 GitHub 仓库的 star数、fork数、open issues 等基础指标",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "格式: owner/repo，例如 anthropics/claude-code"}
            },
            "required": ["repo"],
        },
    },
    {
        "name": "fetch_github_commits",
        "description": "获取 GitHub 仓库最近的 commit 记录",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "格式: owner/repo"}
            },
            "required": ["repo"],
        },
    },
]

TOOL_MAP = {
    "fetch_github_repo": lambda inp: _fetch_github_repo(inp["repo"]),
    "fetch_github_commits": lambda inp: _fetch_github_commits(inp["repo"]),
}


# ── Agent 主函数 ──────────────────────────────────────────────────────────────

async def run_github_agent(client: anthropic.AsyncAnthropic, repo: str, model: str) -> dict:
    """运行 GitHub Sub-Agent，返回结构化指标字典"""
    messages = [
        {
            "role": "user",
            "content": (
                f"请获取 GitHub 仓库 `{repo}` 的以下信息：\n"
                "1. 基础指标：star数、fork数、open issues、watcher数\n"
                "2. 最近 10 条 commit\n\n"
                "请调用工具获取数据，最后以 JSON 格式返回所有收集到的数据，"
                "键名使用：stars, forks, open_issues, watchers, description, recent_commits"
            ),
        }
    ]

    # Agentic loop
    while True:
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            tools=TOOLS,
            messages=messages,
        )

        # 没有工具调用 → 返回最终结果
        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    # 尝试从文本中提取 JSON
                    text = block.text.strip()
                    try:
                        start = text.index("{")
                        end = text.rindex("}") + 1
                        return json.loads(text[start:end])
                    except (ValueError, json.JSONDecodeError):
                        return {"raw": text}
            return {}

        # 有工具调用 → 执行工具并回传结果
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
