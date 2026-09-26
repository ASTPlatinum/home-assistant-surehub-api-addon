"""Home Assistant add-on extensions for the upstream SureHub API.

Adds convenience endpoints for pet access and location while reusing the
upstream SureHub API authentication, token cache, request handling, and
configured endpoint.
"""

from typing import Any

from surehub_api.config import settings
from surehub_api.entities import dto, official
from surehub_api.main import app
from surehub_api.services import api, pets
from surehub_api.utils import response_handler

PROFILE_NORMAL = 2
PROFILE_INDOOR_ONLY = 3

BATTERY_VOLTAGE_FULL_PER_CELL = 1.6
BATTERY_VOLTAGE_LOW_PER_CELL = 1.2
BATTERY_CELL_COUNT = 4


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


def _battery_percent(voltage: float | int | None) -> int | None:
    """Estimate battery percentage using the same 4-cell curve as surepy."""
    if voltage is None:
        return None

    voltage_per_cell = float(voltage) / BATTERY_CELL_COUNT
    usable_range = BATTERY_VOLTAGE_FULL_PER_CELL - BATTERY_VOLTAGE_LOW_PER_CELL
    percent = int(
        ((voltage_per_cell - BATTERY_VOLTAGE_LOW_PER_CELL) / usable_range) * 100
    )
    return max(0, min(percent, 100))


def _get_battery_devices() -> list[dict[str, Any]]:
    uri = f"{settings.endpoint}/api/device"
    response = api.get(uri)
    response_handler.raise_for_status(response)

    payload = response.json()
    raw_devices = payload.get("data", []) if isinstance(payload, dict) else payload

    devices: list[dict[str, Any]] = []
    for device in raw_devices:
        status = device.get("status") or {}
        battery_voltage = status.get("battery")

        try:
            battery_voltage = (
                float(battery_voltage) if battery_voltage is not None else None
            )
        except (TypeError, ValueError):
            battery_voltage = None

        devices.append(
            {
                "id": device.get("id"),
                "name": device.get("name"),
                "product_id": device.get("product_id"),
                "serial_number": device.get("serial_number"),
                "online": device.get("online"),
                "battery_voltage": battery_voltage,
                "battery_percent": _battery_percent(battery_voltage),
            }
        )

    return devices


def _set_pet_position(
    pet_id: int,
    position: official.PetPositionWhere,
) -> dict[str, Any]:
    payload = dto.UpdatePetStateRequest(position=position)
    pets.update_pet_state(pet_id, payload)

    return {
        "ok": True,
        "pet_id": pet_id,
        "position": int(position),
        "location": "inside" if position == official.PetPositionWhere.INSIDE else "outside",
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


@app.post(
    "/pets/{pet_id}/inside",
    tags=["Pet location"],
    summary="Set pet location to inside",
)
def set_pet_inside(pet_id: int) -> dict[str, Any]:
    return _set_pet_position(pet_id, official.PetPositionWhere.INSIDE)


@app.post(
    "/pets/{pet_id}/outside",
    tags=["Pet location"],
    summary="Set pet location to outside",
)
def set_pet_outside(pet_id: int) -> dict[str, Any]:
    return _set_pet_position(pet_id, official.PetPositionWhere.OUTSIDE)


@app.get(
    "/batteries",
    tags=["Battery"],
    summary="Get Sure Petcare device battery levels",
)
def get_batteries() -> dict[str, Any]:
    devices = _get_battery_devices()
    return {
        "count": len(devices),
        "battery_device_count": sum(
            1 for device in devices if device["battery_voltage"] is not None
        ),
        "devices": devices,
    }
