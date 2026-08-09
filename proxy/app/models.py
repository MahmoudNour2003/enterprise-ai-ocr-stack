"""Pydantic models for OpenAI request and response formats."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ImageUrlDetail(BaseModel):
    """Image URL schema in OpenAI multimodal content."""

    url: str
    detail: Optional[str] = "auto"


class ContentPart(BaseModel):
    """Content part for multimodal messages."""

    type: str
    text: Optional[str] = None
    image_url: Optional[Union[str, ImageUrlDetail, Dict[str, Any]]] = None


class OpenAIChatMessage(BaseModel):
    """Single chat message schema."""

    role: str
    content: Optional[Union[str, List[Union[ContentPart, Dict[str, Any]]]]] = ""
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class OpenAIChatCompletionRequest(BaseModel):
    """OpenAI Chat Completion request payload."""

    model: str
    messages: Optional[List[OpenAIChatMessage]] = Field(default_factory=list)
    tools: Optional[List[Dict[str, Any]]] = None
    prompt: Optional[Union[str, List[Any]]] = None
    input: Optional[Union[str, List[Any]]] = None
    instructions: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


# GET /v1/models response schemas
class OpenAIModelObject(BaseModel):
    """Individual model metadata object."""

    id: str
    object: str = "model"
    owned_by: str = "iti"


class OpenAIModelListResponse(BaseModel):
    """Response format for GET /v1/models."""

    object: str = "list"
    data: List[OpenAIModelObject]


# POST /v1/chat/completions response schemas
class OpenAIFunctionCall(BaseModel):
    """Function call detail in tool call."""

    name: str
    arguments: str


class OpenAIToolCall(BaseModel):
    """Tool call item schema."""

    id: str
    type: str = "function"
    function: OpenAIFunctionCall


class OpenAIChatMessageResponse(BaseModel):
    """Message output schema within completion choice."""

    role: str = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[OpenAIToolCall]] = None


class OpenAIChatChoice(BaseModel):
    """Choice object in chat completion response."""

    index: int = 0
    message: OpenAIChatMessageResponse
    finish_reason: str = "stop"


class OpenAIChatUsage(BaseModel):
    """Usage statistics matching OpenAI format."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIOutputTextContent(BaseModel):
    """Text item within Responses API output format."""

    type: str = "text"
    text: str


class OpenAIOutputItem(BaseModel):
    """Output message item schema for Responses API."""

    type: str = "message"
    role: str = "assistant"
    content: List[Union[OpenAIOutputTextContent, Dict[str, Any], str]] = Field(default_factory=list)


class OpenAIChatCompletionResponse(BaseModel):
    """Full OpenAI Chat Completion & Responses API response payload."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChatChoice] = Field(default_factory=list)
    output: Optional[List[Union[OpenAIOutputItem, Dict[str, Any]]]] = None
    status: Optional[str] = "completed"
    usage: OpenAIChatUsage


# Error schemas
class OpenAIErrorDetail(BaseModel):
    """Standardized OpenAI error details."""

    message: str
    type: str = "invalid_request_error"
    param: Optional[str] = None
    code: Optional[str] = None


class OpenAIErrorResponse(BaseModel):
    """OpenAI top-level error response payload."""

    error: OpenAIErrorDetail
