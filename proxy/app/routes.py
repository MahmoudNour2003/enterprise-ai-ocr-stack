"""API Route Handlers for Enterprise AI Proxy."""

import json
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from app.client import iti_client
from app.converter import (
    convert_iti_to_openai_response,
    convert_openai_to_iti_payload,
    format_openai_error,
)
from app.models import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIChatMessage,
    OpenAIModelListResponse,
    OpenAIModelObject,
)
from app.settings import settings

router = APIRouter()


@router.get("/", summary="Root Status")
async def get_root() -> dict:
    """Returns basic service status."""
    return {"status": "running", "service": "Enterprise AI Proxy"}


@router.get("/health", summary="Health Check")
async def get_health() -> dict:
    """Returns service health state."""
    return {"status": "healthy"}


@router.get(
    "/v1/models",
    response_model=OpenAIModelListResponse,
    summary="List Supported Models",
)
async def list_models() -> OpenAIModelListResponse:
    """Returns list of supported models in OpenAI format."""
    allowed_ids = settings.get_allowed_model_ids()
    model_objects = [
        OpenAIModelObject(id=model_id, object="model", owned_by="iti")
        for model_id in allowed_ids
    ]
    return OpenAIModelListResponse(object="list", data=model_objects)


@router.get(
    "/v1/models/{model_id}",
    response_model=OpenAIModelObject,
    summary="Get Specific Model Details",
)
async def get_model(model_id: str) -> OpenAIModelObject:
    """Returns model metadata object."""
    return OpenAIModelObject(id=model_id, object="model", owned_by="iti")


@router.post(
    "/v1/chat/completions",
    response_model=OpenAIChatCompletionResponse,
    summary="Create Chat Completion",
)
@router.post(
    "/v1/responses",
    response_model=OpenAIChatCompletionResponse,
    summary="Create Responses Completion",
)
@router.post(
    "/v1/completions",
    response_model=OpenAIChatCompletionResponse,
    summary="Create Text Completion",
)
async def create_chat_completion(
    request: OpenAIChatCompletionRequest,
):
    """Handles OpenAI Chat Completion requests and forwards to ITI Enterprise AI."""
    from app.utils import logger
    logger.info(f"RAW OPENAI REQUEST PAYLOAD FROM N8N: {request.model_dump()}")

    if request.stream:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=format_openai_error(
                message="Streaming not implemented.",
                error_type="not_implemented",
            ),
        )

    endpoint, iti_payload = convert_openai_to_iti_payload(request)

    logger.info(f"Sending request to ITI API endpoint {endpoint} with {len(iti_payload.get('messages', []))} messages.")
    for idx, m in enumerate(iti_payload.get("messages", [])):
        logger.info(f"  Msg [{idx}] role={m.get('role')}: {m.get('content')[:150] if m.get('content') else 'EMPTY'}")

    iti_response_data, status_code, latency_ms = await iti_client.send_chat_request(
        endpoint=endpoint,
        payload=iti_payload,
    )

    logger.info(f"Raw ITI API Response: {iti_response_data}")

    openai_response = convert_iti_to_openai_response(
        iti_response=iti_response_data,
        requested_model=request.model,
        requested_tools=request.tools,
    )

    # Multi-turn tool execution loop inside the proxy (up to 3 turns)
    for _turn in range(3):
        choice = openai_response.choices[0]
        if choice.finish_reason != "tool_calls" or not choice.message.tool_calls:
            break

        tc = choice.message.tool_calls[0]
        tool_name = tc.function.name
        try:
            tool_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
        except Exception:
            tool_args = {}

        if "toolName" in tool_args:
            sub_name = tool_args.get("toolName")
            sub_params = tool_args.get("toolParameters", {})
            if sub_name:
                tool_name = sub_name
                tool_args = sub_params

        # Extract user_id from system prompt or messages for session context RLS
        user_id = None
        sys_prompt = iti_payload.get("system_prompt", "")
        import re
        match = re.search(r"User\s*ID:\s*(\d+)", sys_prompt, re.IGNORECASE)
        if match:
            user_id = int(match.group(1))
        elif hasattr(request, "input") and isinstance(request.input, list):
            for item in request.input:
                if isinstance(item, dict):
                    m_text = str(item.get("content", ""))
                    m_match = re.search(r"User\s*ID:\s*(\d+)", m_text, re.IGNORECASE)
                    if m_match:
                        user_id = int(m_match.group(1))
                        break

        logger.info(f"Proxy Turn {_turn + 1}: Intercepted tool call '{tool_name}' with args {tool_args} for userId {user_id}. Executing via MCP...")
        from app.mcp_executor import execute_mcp_tool
        tool_result = await execute_mcp_tool(tool_name, tool_args, user_id=user_id)
        logger.info(f"Proxy Turn {_turn + 1} MCP Tool Execution Result ({len(tool_result)} bytes): {tool_result[:200]}...")

        if request.messages is None:
            request.messages = []

        request.messages.append(
            OpenAIChatMessage(
                role="assistant",
                content=f"Executed tool {tool_name} with arguments {json.dumps(tool_args)}"
            )
        )

        if tool_name in ["list_tables", "describe_table"]:
            next_instruction = f"[DATABASE SCHEMA FOR {tool_name}]:\n{tool_result}\n\nINSTRUCTION: You have retrieved the table schema above. Now construct and execute your safe SELECT query using execute_select to fetch the actual invoice and purchase order records for the user."
        else:
            next_instruction = f"[DATABASE QUERY RESULT FOR {tool_name}]:\n{tool_result}\n\nINSTRUCTION: The database query has completed above. Use this data to answer the user's request directly in clear natural language."

        request.messages.append(
            OpenAIChatMessage(
                role="user",
                content=next_instruction
            )
        )

        endpoint_next, iti_payload_next = convert_openai_to_iti_payload(request)
        iti_response_data_next, _, _ = await iti_client.send_chat_request(
            endpoint=endpoint_next,
            payload=iti_payload_next,
        )
        openai_response = convert_iti_to_openai_response(
            iti_response=iti_response_data_next,
            requested_model=request.model,
            requested_tools=request.tools if _turn == 0 else None,
        )

    return openai_response
