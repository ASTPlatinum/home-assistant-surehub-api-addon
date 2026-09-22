"""Home Assistant add-on extensions for the upstream SureHub API.

Adds per-tag access mode endpoints while reusing the upstream SureHub API
authentication, token cache, request handling, and configured endpoint.
"""

from typing import Any

from surehub_api.config import settings
from surehub_api.main import app
from surehub_api.services import api
from surehub_api.utils import response_handler

PROFILE_NORMAL = 2
PROFILE_INDOOR_ONLY = 3


def _set_tag_profile(device_id: int, tag_id: int, profile: int) -> dict[str, Any]:
    if profile not in (PROFILE_NORMAL, PROFILE_INDOOR_ONLY):
        raise ValueError("Unsupported tag profile")

    uri = f"{settings.endpoint}/api/v2/device/{device_id}/tag/async"
    payload = [
        {
            "tag_id": tag_id,
            "request_action": 0,
            "profile": profile,
        }
    ]

    response = api.put(uri, json=payload)
    response_handler.raise_for_status(response)

    upstream_response: Any = None
    if response.content:
        try:
            upstream_response = response.json()
        except ValueError:
            upstream_response = response.text

    return {
        "ok": True,
        "device_id": device_id,
        "tag_id": tag_id,
        "profile": profile,
        "mode": "indoor_only" if profile == PROFILE_INDOOR_ONLY else "normal",
        "upstream_response": upstream_response,
    }


@app.post(
    "/devices/{device_id}/tags/{tag_id}/indoor-only",
    tags=["Pet access"],
    summary="Set tag to indoor-only",
)
def set_tag_indoor_only(device_id: int, tag_id: int) -> dict[str, Any]:
    return _set_tag_profile(device_id, tag_id, PROFILE_INDOOR_ONLY)


@app.post(
    "/devices/{device_id}/tags/{tag_id}/normal",
    tags=["Pet access"],
    summary="Set tag to normal access",
)
def set_tag_normal(device_id: int, tag_id: int) -> dict[str, Any]:
    return _set_tag_profile(device_id, tag_id, PROFILE_NORMAL)
