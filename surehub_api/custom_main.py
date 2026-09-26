"""Home Assistant app extensions for the upstream SureHub API.

Adds convenience endpoints for pet access and location, battery reporting,
and MQTT Discovery for Sure Petcare battery sensors.
"""

import atexit
import json
import logging
import os
import threading
from typing import Any

from paho.mqtt import client as mqtt

from surehub_api.config import settings
from surehub_api.entities import dto, official
from surehub_api.main import app
from surehub_api.services import api, pets
from surehub_api.utils import response_handler

LOGGER = logging.getLogger("surehub_mqtt")

PROFILE_NORMAL = 2
PROFILE_INDOOR_ONLY = 3

BATTERY_VOLTAGE_FULL_PER_CELL = 1.6
BATTERY_VOLTAGE_LOW_PER_CELL = 1.2
BATTERY_CELL_COUNT = 4

MQTT_DISCOVERY_PREFIX = "homeassistant"
MQTT_TOPIC_PREFIX = "surehub"
_mqtt_stop_event = threading.Event()
_mqtt_thread: threading.Thread | None = None


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
                "online": device.get("online", status.get("online")),
                "battery_voltage": battery_voltage,
                "battery_percent": _battery_percent(battery_voltage),
            }
        )

    return devices


def _mqtt_publish_device(
    client: mqtt.Client,
    device: dict[str, Any],
) -> None:
    """Publish one battery device using Home Assistant MQTT Discovery."""
    device_id = device["id"]
    if device_id is None or device["battery_voltage"] is None:
        return

    object_id = f"surehub_{device_id}_battery"
    state_topic = f"{MQTT_TOPIC_PREFIX}/devices/{device_id}/battery"
    availability_topic = f"{MQTT_TOPIC_PREFIX}/devices/{device_id}/availability"
    discovery_topic = (
        f"{MQTT_DISCOVERY_PREFIX}/sensor/{object_id}/config"
    )

    discovery_payload = {
        "name": "Battery",
        "unique_id": object_id,
        "default_entity_id": f"sensor.{object_id}",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "suggested_display_precision": 0,
        "entity_category": "diagnostic",
        "state_topic": state_topic,
        "value_template": "{{ value_json.battery_percent }}",
        "json_attributes_topic": state_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": {
            "identifiers": [f"surehub_{device_id}"],
            "name": device.get("name") or f"SureHub device {device_id}",
            "manufacturer": "Sure Petcare",
            "model": f"Product {device.get('product_id')}",
        },
        "origin": {
            "name": "SureHub API",
            "sw": "0.4.0",
            "url": "https://github.com/ASTPlatinum/home-assistant-surehub-api-addon",
        },
    }

    state_payload = {
        "battery_percent": device["battery_percent"],
        "battery_voltage": device["battery_voltage"],
        "online": device.get("online"),
        "device_id": device_id,
        "product_id": device.get("product_id"),
        "serial_number": device.get("serial_number"),
    }

    client.publish(
        discovery_topic,
        json.dumps(discovery_payload),
        qos=1,
        retain=True,
    )
    client.publish(
        state_topic,
        json.dumps(state_payload),
        qos=1,
        retain=True,
    )
    client.publish(
        availability_topic,
        "online" if device.get("online") is not False else "offline",
        qos=1,
        retain=True,
    )


def _mqtt_publish_all(client: mqtt.Client) -> None:
    """Publish battery sensors for devices that actually report a battery."""
    battery_devices = [
        device
        for device in _get_battery_devices()
        if device["battery_voltage"] is not None
    ]

    for device in battery_devices:
        _mqtt_publish_device(client, device)

    LOGGER.info(
        "Published %d SureHub battery sensor(s) through MQTT Discovery",
        len(battery_devices),
    )


def _mqtt_worker() -> None:
    host = os.getenv("SUREHUB_MQTT_HOST")
    if not host:
        LOGGER.info("MQTT Discovery disabled because no MQTT service is available")
        return

    port = int(os.getenv("SUREHUB_MQTT_PORT", "1883"))
    username = os.getenv("SUREHUB_MQTT_USER") or None
    password = os.getenv("SUREHUB_MQTT_PASSWORD") or None
    refresh_seconds = max(
        60,
        int(os.getenv("SUREHUB_MQTT_REFRESH_SECONDS", "300")),
    )

    while not _mqtt_stop_event.is_set():
        client: mqtt.Client | None = None
        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id="surehub-api",
            )

            if username:
                client.username_pw_set(username, password)

            client.will_set(
                f"{MQTT_TOPIC_PREFIX}/status",
                "offline",
                qos=1,
                retain=True,
            )
            client.connect(host, port, keepalive=60)
            client.loop_start()
            client.publish(
                f"{MQTT_TOPIC_PREFIX}/status",
                "online",
                qos=1,
                retain=True,
            )

            LOGGER.info("Connected to MQTT broker at %s:%s", host, port)

            while not _mqtt_stop_event.is_set():
                try:
                    _mqtt_publish_all(client)
                except Exception:
                    LOGGER.exception("Failed to refresh SureHub MQTT battery sensors")

                _mqtt_stop_event.wait(refresh_seconds)

        except Exception:
            LOGGER.exception("MQTT connection failed; retrying in 30 seconds")
            _mqtt_stop_event.wait(30)

        finally:
            if client is not None:
                try:
                    client.loop_stop()
                    client.disconnect()
                except Exception:
                    pass


def _start_mqtt() -> None:
    global _mqtt_thread

    if not os.getenv("SUREHUB_MQTT_HOST"):
        LOGGER.info("MQTT Discovery is not configured")
        return

    if _mqtt_thread is not None and _mqtt_thread.is_alive():
        return

    _mqtt_stop_event.clear()
    _mqtt_thread = threading.Thread(
        target=_mqtt_worker,
        name="surehub-mqtt",
        daemon=True,
    )
    _mqtt_thread.start()


def _stop_mqtt() -> None:
    _mqtt_stop_event.set()
    if _mqtt_thread is not None:
        _mqtt_thread.join(timeout=5)


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
        "location": (
            "inside"
            if position == official.PetPositionWhere.INSIDE
            else "outside"
        ),
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


_start_mqtt()
atexit.register(_stop_mqtt)
