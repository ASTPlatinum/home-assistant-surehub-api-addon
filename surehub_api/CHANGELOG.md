# Changelog

## 0.4.1

- Fix startup crash with FastAPI 0.136+, where `add_event_handler` is no longer available on the app object.
- Start the MQTT discovery worker directly when the app module loads.
- Register MQTT shutdown cleanup with Python `atexit` instead of FastAPI lifecycle hooks.

## 0.4.0

- Add automatic Home Assistant battery entities through MQTT Discovery.
- Use the Home Assistant Supervisor MQTT service connection, so no broker credentials need to be entered in the SureHub app.
- Publish one battery sensor per Sure Petcare device that reports a battery.
- Do not create a battery sensor for the Sure Petcare hub because it has no battery value.
- Publish battery voltage, online state, device ID, product ID, and serial number as sensor attributes.
- Refresh Sure Petcare battery readings every 5 minutes.
- Add the Sure Petcare device name to the Home Assistant MQTT device registry entry.

## 0.3.2

- Add `GET /batteries` with each Sure Petcare device name, ID, product ID, serial number, online state, raw battery voltage, and estimated battery percentage.
- Battery percentage uses the established surepy 4-cell calculation: 1.2 V per cell = 0% and 1.6 V per cell = 100%, clamped to 0–100%.
- Devices without a battery, such as the hub, are still returned with null battery values.
- Remove the temporary raw-device debug endpoint now that the battery field has been identified.

## 0.3.1

- Add temporary raw device endpoint at `GET /debug/devices/raw`.
- This exposes the unfiltered Sure Petcare device payload so fields such as battery data can be identified.
- Use a non-conflicting `/debug` path because `/devices/{device_id}` treats arbitrary text after `/devices/` as a device ID.


## 0.3.0

- Add convenience endpoints for manually setting a pet location.
- Add `POST /pets/{pet_id}/inside`.
- Add `POST /pets/{pet_id}/outside`.
- Reuse the upstream SureHub pet-state service for location changes.
- Document Home Assistant REST command examples for pet location control.


## 0.2.0

- Add per-cat indoor-only access control.
- Add `POST /devices/{device_id}/tags/{tag_id}/indoor-only`.
- Add `POST /devices/{device_id}/tags/{tag_id}/normal`.
- Reuse the upstream SureHub API authentication and token handling for access-mode changes.
- Start the extended API through `custom_main.py`.
- Document Home Assistant REST command examples for pet access control.

## 0.1.0

- Initial Home Assistant app/add-on release.
- Wrap the unofficial `fabieu/surehub-api` project.
- Add configurable Sure Petcare account credentials and local API port.
- Expose the SureHub REST API and Swagger documentation on port 3001.
