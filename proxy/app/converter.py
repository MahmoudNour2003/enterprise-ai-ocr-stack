"""Payload conversion utilities between OpenAI and ITI API specifications."""

import time
import uuid
from typing import Any, Dict, List, Tuple
from proxy.app.models import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIChatChoice,
    OpenAIChatMessage,
    OpenAIChatMessageResponse,
    OpenAIChatUsage,
    OpenAIErrorDetail,
    OpenAIErrorResponse,
    OpenAIOutputItem,
    OpenAIOutputTextContent,
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

    # If messages list is empty but prompt or input is provided
    if not messages_list:
        fallback_input = request.input or request.prompt
        if fallback_input:
            if isinstance(fallback_input, str):
                messages_list = [OpenAIChatMessage(role="user", content=fallback_input)]
            elif isinstance(fallback_input, list):
                combined = []
                for item in fallback_input:
                    if isinstance(item, str):
                        combined.append(item)
                    elif isinstance(item, dict):
                        if "content" in item:
                            combined.append(str(item["content"]))
                        elif "text" in item:
                            combined.append(str(item["text"]))
                messages_list = [OpenAIChatMessage(role="user", content="\n".join(combined))]

    for msg in messages_list:
        role = msg.role.lower()
        raw_content = msg.content

        text_parts = []
        if isinstance(raw_content, str):
            text_parts.append(raw_content)
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

        combined_text = "\n".join(text_parts).strip()

        if role == "system":
            if not system_prompt_found:
                system_prompt = combined_text
                system_prompt_found = True
            continue

        cleaned_messages.append({"role": msg.role, "content": combined_text})

    # Ensure ITI receives at least one message in messages array
    if not cleaned_messages:
        fallback_text = system_prompt if system_prompt else "Hello"
        cleaned_messages.append({"role": "user", "content": fallback_text})

    return system_prompt, cleaned_messages, extracted_images


def convert_openai_to_iti_payload(
    request: OpenAIChatCompletionRequest,
) -> Tuple[str, Dict[str, Any]]:
    """Converts OpenAI request payload into ITI request payload."""
    system_prompt, messages, images = extract_system_prompt_and_clean_messages(request)

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
    """Strips conversational preambles (e.g. 'We will now output using tool.')"""
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


def convert_iti_to_openai_response(
    iti_response: Dict[str, Any], requested_model: str
) -> OpenAIChatCompletionResponse:
    """Converts ITI response object back to OpenAI ChatCompletion & Responses format."""
    request_id = iti_response.get("request_id") or f"chatcmpl-{uuid.uuid4().hex[:12]}"
    model_id = iti_response.get("model_id") or requested_model

    raw_output_text = (
        iti_response.get("output_text")
        or iti_response.get("text")
        or iti_response.get("content")
        or ""
    )
    output_text = clean_json_output_text(raw_output_text)

    usage_data = iti_response.get("usage", {})
    prompt_tokens = usage_data.get("input_tokens", usage_data.get("prompt_tokens", 0))
    completion_tokens = usage_data.get("output_tokens", usage_data.get("completion_tokens", 0))
    total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)

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
        choices=[
            OpenAIChatChoice(
                index=0,
                message=OpenAIChatMessageResponse(role="assistant", content=output_text),
                finish_reason="stop",
            )
        ],
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
    """Formats error into OpenAI error schema."""
    return OpenAIErrorResponse(
        error=OpenAIErrorDetail(message=message, type=error_type, param=param, code=code)
    ).model_dump()
