"""Payload conversion utilities between OpenAI and ITI API specifications."""

import json
import time
import uuid
from typing import Any, Dict, List, Tuple, Optional
from app.models import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIChatChoice,
    OpenAIChatMessage,
    OpenAIChatMessageResponse,
    OpenAIChatUsage,
    OpenAIErrorDetail,
    OpenAIErrorResponse,
    OpenAIFunctionCall,
    OpenAIOutputItem,
    OpenAIOutputTextContent,
    OpenAIToolCall,
)


def extract_system_prompt_and_clean_messages(
    request: OpenAIChatCompletionRequest,
) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    """Extracts system prompt, cleans non-system messages, and collects images."""
    system_prompt = ""
    cleaned_messages = []
    extracted_images = []
    system_prompt_found = False

    if request.instructions and not system_prompt_found:
        system_prompt = str(request.instructions)
        system_prompt_found = True

    messages_list = request.messages or []

    if not messages_list:
        fallback_input = request.input or request.prompt
        if fallback_input:
            if isinstance(fallback_input, str):
                messages_list = [OpenAIChatMessage(role="user", content=fallback_input)]
            elif isinstance(fallback_input, list):
                messages_list = []
                for item in fallback_input:
                    if isinstance(item, str):
                        messages_list.append(OpenAIChatMessage(role="user", content=item))
                    elif isinstance(item, dict):
                        role = item.get("role", "user")
                        content = item.get("content", item.get("text", ""))
                        messages_list.append(OpenAIChatMessage(role=role, content=content))

    for msg in messages_list:
        role = msg.role.lower()
        raw_content = msg.content

        text_parts = []
        if isinstance(raw_content, str):
            if raw_content:
                text_parts.append(raw_content)
        elif isinstance(raw_content, (dict, int, float, bool)):
            text_parts.append(json.dumps(raw_content))
        elif isinstance(raw_content, list):
            for item in raw_content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    item_type = item.get("type", "")
                    if item_type == "text" and "text" in item:
                        text_parts.append(item["text"] or "")
                    elif item_type == "image_url" or "image_url" in item:
                        img_data = item.get("image_url")
                        if isinstance(img_data, str):
                            extracted_images.append(img_data)
                        elif isinstance(img_data, dict) and "url" in img_data:
                            extracted_images.append(img_data["url"])
                    else:
                        text_parts.append(json.dumps(item))
                elif hasattr(item, "type"):
                    item_type = getattr(item, "type", "")
                    if item_type == "text" and hasattr(item, "text") and item.text:
                        text_parts.append(item.text)
                    elif item_type == "image_url" or hasattr(item, "image_url"):
                        img_data = getattr(item, "image_url", None)
                        if isinstance(img_data, str):
                            extracted_images.append(img_data)
                        elif isinstance(img_data, dict) and "url" in img_data:
                            extracted_images.append(img_data["url"])
                        elif hasattr(img_data, "url"):
                            extracted_images.append(getattr(img_data, "url"))
                    else:
                        text_parts.append(str(item))
                else:
                    text_parts.append(str(item))
        elif raw_content is not None:
            text_parts.append(str(raw_content))

        combined_text = "\n".join(text_parts).strip()

        if role == "system":
            if not system_prompt_found:
                system_prompt = combined_text
                system_prompt_found = True
            continue
        elif role == "tool":
            tool_id = getattr(msg, "tool_call_id", None) or getattr(msg, "name", None) or "tool"
            cleaned_messages.append(
                {
                    "role": "user",
                    "content": f"[DATABASE QUERY RESULT FOR {tool_id}]:\n{combined_text}\n\nINSTRUCTION: The database query has completed above. Use this data to answer the user's request directly in natural language. DO NOT call any more tools.",
                }
            )
            continue
        elif role == "assistant" and getattr(msg, "tool_calls", None):
            try:
                tc_list = getattr(msg, "tool_calls", [])
                if isinstance(tc_list, list):
                    serialized = []
                    for item in tc_list:
                        if hasattr(item, "model_dump"):
                            serialized.append(item.model_dump())
                        elif isinstance(item, dict):
                            serialized.append(item)
                        else:
                            serialized.append(str(item))
                    tool_calls_text = json.dumps(serialized)
                else:
                    tool_calls_text = str(tc_list)
            except Exception:
                tool_calls_text = str(getattr(msg, "tool_calls", ""))

            cleaned_messages.append(
                {
                    "role": "assistant",
                    "content": f"Tool call requested: {tool_calls_text}" if not combined_text else f"{combined_text}\nTool call requested: {tool_calls_text}",
                }
            )
            continue

        cleaned_messages.append(
            {
                "role": msg.role,
                "content": combined_text,
            }
        )

    if not cleaned_messages:
        fallback_text = system_prompt if system_prompt else "Hello"
        cleaned_messages.append(
            {
                "role": "user",
                "content": fallback_text,
            }
        )

    return system_prompt, cleaned_messages, extracted_images


def convert_openai_to_iti_payload(
    request: OpenAIChatCompletionRequest,
) -> Tuple[str, Dict[str, Any]]:
    """Converts OpenAI request payload into ITI request payload and determines endpoint."""
    system_prompt, messages, images = extract_system_prompt_and_clean_messages(request)

    if request.tools:
        tools_list = []
        for t in request.tools:
            if t.get("type") == "function" and "function" in t:
                f = t["function"]
                tools_list.append(
                    f"- Tool Name: {f.get('name')}\n  Description: {f.get('description', '')}\n  Parameters: {json.dumps(f.get('parameters', {}))}"
                )
        if "DATABASE SCHEMA DEFINITION" not in system_prompt:
            schema_context = (
                "\n\n### DATABASE SCHEMA DEFINITION:\n"
                "1. Invoices: (Id, InvoiceNumber, VendorId, PurchaseOrderId, Status [1=Uploaded, 7=Completed, 9=NeedsReview], TotalAmount, Subtotal, Vat, Currency, InvoiceDate, UploadedByUserId, VendorName)\n"
                "2. PurchaseOrders: (Id, OrderNumber, VendorId, RequestedByUserId, Status [1=Draft, 2=PendingApproval, 3=Approved], TotalAmount, OrderDate, ExpectedDeliveryDate)\n"
                "3. InvoiceItems: (Id, InvoiceId, ProductId, Description, Quantity, UnitPrice, LineTotal, SupplierSku)\n"
                "4. PurchaseOrderItems: (Id, PurchaseOrderId, ProductId, Quantity, UnitPrice, LineTotal, Amount)\n"
                "5. Discrepancies: (Id, InvoiceId, InvoiceItemId, DiscrepancyType [4=UnitPriceMismatch], FieldName, ExpectedValue, ActualValue, IsResolved)\n"
                "6. Vendors: (Id, Name, TaxRegistrationNumber, ContactEmail, ContactPhone, Address, IsApproved)\n"
                "7. Products: (Id, Name, SkuSupplier, Description, UnitPrice, Uom, VendorId)\n"
                "8. Users_Domain: (Id, FullName, Email, RoleName, IdentityId)\n\n"
                "### CRITICAL TOOL EXECUTION RULE:\n"
                "You ALREADY HAVE the complete table schema above. DO NOT call list_tables() or describe_table().\n"
                "For ANY user request, you MUST immediately call execute_select with a valid SELECT query!\n"
                'Format: {"function": "execute_select", "arguments": {"sql": "SELECT ... FROM ...;"}}\n\n'
                "### RLS & QUERY RULE:\n"
                "Row-Level Security (RLS) is automatically enforced at the database level by SQL Server for the authenticated user.\n"
                "DO NOT write placeholders like [YOUR_USER_ID] or ask the user for their ID.\n"
                "Simply execute standard SELECT queries (e.g. `SELECT * FROM Invoices;` or `SELECT * FROM PurchaseOrders;`), and SQL Server will automatically isolate and return only the records belonging to the active user."
            )
            system_prompt += schema_context

    payload: Dict[str, Any] = {
        "model_id": request.model,
        "system_prompt": system_prompt,
        "messages": messages,
    }

    if request.temperature is not None:
        payload["temperature"] = request.temperature

    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens

    if images:
        payload["images"] = images
        endpoint = "/student/multimodal-chat"
    else:
        endpoint = "/student/chat"

    return endpoint, payload


def clean_json_output_text(text: str) -> str:
    """Strips conversational preambles or markdown backticks so n8n receives clean output."""
    if not text:
        return text

    stripped = text.strip()

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        preamble = stripped[:first_brace].strip()
        if preamble:
            return stripped[first_brace : last_brace + 1]

    first_bracket = stripped.find("[")
    last_bracket = stripped.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        preamble = stripped[:first_bracket].strip()
        if preamble:
            return stripped[first_bracket : last_bracket + 1]

    return stripped


import re


def try_parse_tool_call(output_text: str) -> Tuple[bool, Optional[OpenAIToolCall]]:
    """Attempts to parse output_text as a JSON tool call, extracting valid JSON objects even if reasoning/tags are present."""
    if not output_text:
        return False, None

    cleaned = clean_json_output_text(output_text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            func_name = data.get("function") or data.get("name") or data.get("tool")
            if func_name and isinstance(func_name, str):
                args = data.get("arguments") or data.get("parameters") or data.get("args") or {}
                args_str = json.dumps(args) if isinstance(args, dict) else str(args)
                return True, OpenAIToolCall(
                    id=f"call_{uuid.uuid4().hex[:12]}",
                    type="function",
                    function=OpenAIFunctionCall(name=func_name, arguments=args_str),
                )
    except Exception:
        pass

    # Regex search for {"function": "...", ...} or {"name": "...", ...}
    match = re.search(
        r'\{\s*"(?:function|name|tool)"\s*:\s*"([^"]+)"\s*(?:,\s*"(?:arguments|parameters|args)"\s*:\s*(\{.*?\}|"[^"]*"))?\s*\}',
        output_text,
        re.DOTALL,
    )
    if match:
        func_name = match.group(1)
        args_raw = match.group(2) or "{}"
        try:
            args_data = json.loads(args_raw)
            args_str = json.dumps(args_data) if isinstance(args_data, dict) else str(args_data)
        except Exception:
            args_str = "{}"

        return True, OpenAIToolCall(
            id=f"call_{uuid.uuid4().hex[:12]}",
            type="function",
            function=OpenAIFunctionCall(name=func_name, arguments=args_str),
        )

    # Fallback: Check if model outputted a SELECT SQL block inside ```sql ... ```
    sql_match = re.search(r'```(?:sql)?\s*(SELECT\s+.*?)```', output_text, re.IGNORECASE | re.DOTALL)
    if not sql_match:
        sql_match = re.search(r'\b(SELECT\s+[\s\S]+?;)', output_text, re.IGNORECASE)

    if sql_match:
        extracted_sql = sql_match.group(1).strip()
        args_str = json.dumps({"sql": extracted_sql})
        return True, OpenAIToolCall(
            id=f"call_{uuid.uuid4().hex[:12]}",
            type="function",
            function=OpenAIFunctionCall(name="execute_select", arguments=args_str),
        )

    return False, None


def extract_native_tool_calls(iti_response: Dict[str, Any]) -> List[OpenAIToolCall]:
    """Extracts tool calls if returned natively in ITI API response dictionary."""
    tool_calls: List[OpenAIToolCall] = []

    raw_tc = (
        iti_response.get("tool_calls")
        or iti_response.get("tool_use")
        or iti_response.get("function_call")
        or iti_response.get("tools")
    )
    if isinstance(raw_tc, list):
        for item in raw_tc:
            if isinstance(item, dict):
                func = item.get("function", {})
                name = func.get("name") or item.get("name")
                args = func.get("arguments") or item.get("arguments") or item.get("input") or {}
                if name:
                    tool_calls.append(
                        OpenAIToolCall(
                            id=item.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                            type="function",
                            function=OpenAIFunctionCall(
                                name=name,
                                arguments=json.dumps(args) if isinstance(args, dict) else str(args),
                            ),
                        )
                    )
    elif isinstance(raw_tc, dict):
        name = raw_tc.get("name") or raw_tc.get("function")
        args = raw_tc.get("input") or raw_tc.get("arguments") or raw_tc.get("parameters") or {}
        if name:
            tool_calls.append(
                OpenAIToolCall(
                    id=raw_tc.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                    type="function",
                    function=OpenAIFunctionCall(
                        name=name,
                        arguments=json.dumps(args) if isinstance(args, dict) else str(args),
                    ),
                )
            )

    return tool_calls


def convert_iti_to_openai_response(
    iti_response: Dict[str, Any], requested_model: str, requested_tools: Optional[List[Dict[str, Any]]] = None
) -> OpenAIChatCompletionResponse:
    """Converts ITI API JSON response to standard OpenAI ChatCompletionResponse object."""
    request_id = iti_response.get("request_id") or f"chatcmpl-{uuid.uuid4().hex[:12]}"
    model_id = iti_response.get("model_id") or requested_model

    raw_output_text = (
        iti_response.get("output_text")
        or iti_response.get("text")
        or iti_response.get("content")
        or iti_response.get("response")
        or iti_response.get("output")
        or iti_response.get("result")
    )
    if not raw_output_text and isinstance(iti_response.get("data"), dict):
        raw_output_text = (
            iti_response["data"].get("output_text")
            or iti_response["data"].get("text")
            or iti_response["data"].get("content")
        )
    if not raw_output_text and isinstance(iti_response.get("choices"), list) and len(iti_response["choices"]) > 0:
        first_choice = iti_response["choices"][0]
        if isinstance(first_choice, dict):
            if isinstance(first_choice.get("message"), dict):
                raw_output_text = first_choice["message"].get("content")
            elif "text" in first_choice:
                raw_output_text = first_choice.get("text")
    if raw_output_text is None:
        raw_output_text = ""
    output_text = clean_json_output_text(raw_output_text)

    is_tool_call, text_tool_call = try_parse_tool_call(output_text)
    native_tool_calls = extract_native_tool_calls(iti_response)

    if is_tool_call and text_tool_call:
        final_tool_calls = [text_tool_call]
    elif native_tool_calls:
        final_tool_calls = native_tool_calls
    else:
        final_tool_calls = None

    # Override function name and format arguments for n8n container tools (like SQL_MCP_Client_Tools)
    if final_tool_calls and requested_tools and len(requested_tools) > 0:
        n8n_tool_name = requested_tools[0].get("function", {}).get("name")
        if n8n_tool_name:
            for tc in final_tool_calls:
                sub_tool_name = tc.function.name
                try:
                    sub_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                except Exception:
                    sub_args = {}

                tc.function.name = n8n_tool_name
                tc.function.arguments = json.dumps({
                    "toolName": sub_tool_name,
                    "toolParameters": sub_args
                })

    usage_data = iti_response.get("usage", {})
    prompt_tokens = usage_data.get("input_tokens", usage_data.get("prompt_tokens", 0))
    completion_tokens = usage_data.get("output_tokens", usage_data.get("completion_tokens", 0))
    total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

    if final_tool_calls:
        choice = OpenAIChatChoice(
            index=0,
            message=OpenAIChatMessageResponse(
                role="assistant",
                content=None,
                tool_calls=final_tool_calls,
            ),
            finish_reason="tool_calls",
        )
        output_item = OpenAIOutputItem(
            type="message",
            role="assistant",
            content=[OpenAIOutputTextContent(type="text", text=output_text)],
        )
    else:
        choice = OpenAIChatChoice(
            index=0,
            message=OpenAIChatMessageResponse(
                role="assistant",
                content=output_text,
            ),
            finish_reason="stop",
        )
        output_item = OpenAIOutputItem(
            type="message",
            role="assistant",
            content=[OpenAIOutputTextContent(type="text", text=output_text)],
        )

    return OpenAIChatCompletionResponse(
        id=request_id,
        object="chat.completion",
        created=int(time.time()),
        model=model_id,
        choices=[choice],
        output=[output_item],
        status="completed",
        usage=OpenAIChatUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


def format_openai_error(
    message: str, error_type: str = "api_error", param: str = None, code: str = None
) -> Dict[str, Any]:
    """Formats an error response into OpenAI error structure."""
    return OpenAIErrorResponse(
        error=OpenAIErrorDetail(
            message=message,
            type=error_type,
            param=param,
            code=code,
        )
    ).model_dump()
