"""API Route Handlers for Enterprise AI Proxy."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from proxy.app.client import iti_client
from proxy.app.converter import (
    convert_iti_to_openai_response,
    convert_openai_to_iti_payload,
    format_openai_error,
)
from proxy.app.models import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIModelListResponse,
    OpenAIModelObject,
)
from proxy.app.settings import settings

router = APIRouter()


@router.get("/", summary="Root Status")
async def get_root() -> dict:
    return {"status": "running", "service": "Enterprise AI Proxy"}


@router.get("/health", summary="Health Check")
async def get_health() -> dict:
    return {"status": "healthy"}


@router.get("/v1/models", response_model=OpenAIModelListResponse)
async def list_models() -> OpenAIModelListResponse:
    allowed_ids = settings.get_allowed_model_ids()
    model_objects = [
        OpenAIModelObject(id=model_id, object="model", owned_by="iti")
        for model_id in allowed_ids
    ]
    return OpenAIModelListResponse(object="list", data=model_objects)


@router.get("/v1/models/{model_id}", response_model=OpenAIModelObject)
async def get_model(model_id: str) -> OpenAIModelObject:
    return OpenAIModelObject(id=model_id, object="model", owned_by="iti")


@router.post("/v1/chat/completions", response_model=OpenAIChatCompletionResponse)
@router.post("/v1/responses", response_model=OpenAIChatCompletionResponse)
@router.post("/v1/completions", response_model=OpenAIChatCompletionResponse)
async def create_chat_completion(request: OpenAIChatCompletionRequest):
    if request.stream:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=format_openai_error(
                message="Streaming not implemented.",
                error_type="not_implemented",
            ),
        )

    endpoint, iti_payload = convert_openai_to_iti_payload(request)
    iti_response_data, status_code, latency_ms = await iti_client.send_chat_request(
        endpoint=endpoint, payload=iti_payload
    )

    return convert_iti_to_openai_response(
        iti_response=iti_response_data, requested_model=request.model
    )
