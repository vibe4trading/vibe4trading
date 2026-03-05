from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse


def transform_error(error: str) -> str:
    transformations = {
        "prompt_template_id not found": "Prompt template not found",
        "dataset_id not found": "Dataset not found",
        "run_id not found": "Run not found",
        "unknown scenario_set_key": "Invalid scenario set",
        "dexscreener live requires chain_id + pair_id": "Chain ID and Pair ID are required for DexScreener",
        "datasets must be status=ready": "Datasets must be ready before creating a run",
        "dataset windows must match exactly": "All datasets must have matching time windows",
    }

    error_lower = error.lower()
    for pattern, friendly in transformations.items():
        if pattern in error_lower:
            return friendly

    if "dispatch_failed" in error_lower:
        return "Failed to start job. Please try again."

    return error


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        detail = str(exc.detail)
        friendly_detail = transform_error(detail)

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": friendly_detail},
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )
