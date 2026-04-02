"""System Health Sub-Agent — 获取本机 CPU / 内存 / 磁盘指标（真实数据）"""
import json
import anthropic

# ── 工具实现 ──────────────────────────────────────────────────────────────────

def _get_cpu_metrics() -> dict:
    """获取 CPU 使用率和核心数"""
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_count": psutil.cpu_count(),
        "cpu_freq_mhz": round(psutil.cpu_freq().current, 1) if psutil.cpu_freq() else None,
        "load_avg_1m": round(psutil.getloadavg()[0], 2),
    }


def _get_memory_metrics() -> dict:
    """获取内存使用情况"""
    import psutil
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "total_gb": round(vm.total / 1e9, 2),
        "used_gb": round(vm.used / 1e9, 2),
        "available_gb": round(vm.available / 1e9, 2),
        "memory_percent": vm.percent,
        "swap_used_gb": round(sw.used / 1e9, 2),
        "swap_percent": sw.percent,
    }


def _get_disk_metrics() -> dict:
    """获取磁盘使用情况"""
    import psutil
    disk = psutil.disk_usage("/")
    io = psutil.disk_io_counters()
    return {
        "total_gb": round(disk.total / 1e9, 2),
        "used_gb": round(disk.used / 1e9, 2),
        "free_gb": round(disk.free / 1e9, 2),
        "disk_percent": disk.percent,
        "read_mb": round(io.read_bytes / 1e6, 2) if io else None,
        "write_mb": round(io.write_bytes / 1e6, 2) if io else None,
    }


def _get_network_metrics() -> dict:
    """获取网络 IO 统计"""
    import psutil
    net = psutil.net_io_counters()
    try:
        conns = psutil.net_connections()
        active = len([c for c in conns if c.status == "ESTABLISHED"])
    except (psutil.AccessDenied, PermissionError):
        active = None  # macOS 非 root 无权限列举所有连接
    return {
        "bytes_sent_mb": round(net.bytes_sent / 1e6, 2),
        "bytes_recv_mb": round(net.bytes_recv / 1e6, 2),
        "active_connections": active,
    }


# ── 工具定义 ──────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_cpu_metrics",
        "description": "获取当前系统 CPU 使用率、核心数、负载",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_memory_metrics",
        "description": "获取系统内存和 Swap 使用情况",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_disk_metrics",
        "description": "获取磁盘使用情况和读写统计",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_network_metrics",
        "description": "获取网络 IO 统计和活跃连接数",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

TOOL_MAP = {
    "get_cpu_metrics": lambda _: _get_cpu_metrics(),
    "get_memory_metrics": lambda _: _get_memory_metrics(),
    "get_disk_metrics": lambda _: _get_disk_metrics(),
    "get_network_metrics": lambda _: _get_network_metrics(),
}


# ── Agent 主函数 ──────────────────────────────────────────────────────────────

async def run_system_agent(client: anthropic.AsyncAnthropic, model: str) -> dict:
    messages = [
        {
            "role": "user",
            "content": (
                "请获取完整的系统健康状态，包括：\n"
                "1. CPU 使用率和负载\n"
                "2. 内存使用情况\n"
                "3. 磁盘使用情况\n"
                "4. 网络 IO\n\n"
                "最后以 JSON 格式返回所有指标，键名：cpu_percent, cpu_count, load_avg_1m, "
                "memory_percent, memory_used_gb, memory_total_gb, disk_percent, disk_used_gb, "
                "disk_total_gb, bytes_recv_mb, bytes_sent_mb, active_connections"
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
