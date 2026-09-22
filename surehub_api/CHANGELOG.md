# Changelog

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
