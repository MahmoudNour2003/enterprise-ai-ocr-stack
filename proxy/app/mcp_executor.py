"""Direct MCP tool executor for AI Proxy."""

import json
import httpx
from typing import Any, Dict, Optional
from app.utils import logger

MCP_SERVER_URL = "http://localhost:3001"


async def execute_mcp_tool(tool_name: str, tool_args: Dict[str, Any], user_id: Optional[int] = None) -> str:
    """Executes an MCP tool against the SQL MCP Server directly."""
    if user_id is not None and "userId" not in tool_args:
        tool_args["userId"] = user_id

    logger.info(f"Proxy executing MCP tool '{tool_name}' with args: {tool_args}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{MCP_SERVER_URL}/api/tools/execute",
                json={"tool": tool_name, "arguments": tool_args},
            )
            if resp.status_code == 200:
                data = resp.json()
                return json.dumps(data)
            else:
                return f"Error executing tool {tool_name}: HTTP {resp.status_code} - {resp.text}"
    except Exception as exc:
        logger.error(f"Failed to execute MCP tool {tool_name}: {exc}")
        return f"Error executing tool {tool_name}: {exc}"
