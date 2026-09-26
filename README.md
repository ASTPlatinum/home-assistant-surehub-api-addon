# home-assistant-surehub-api-addon
# SureHub API Home Assistant Add-on

A Home Assistant add-on that runs the unofficial SureHub API locally, allowing Home Assistant to query Sure Petcare data through REST endpoints.

This add-on is useful when the official Home Assistant Sure Petcare integration does not expose the sensors or data you need.

## What this add-on does

The add-on runs a local API service inside Home Assistant. It logs into Sure Petcare using your Sure Petcare account credentials and exposes local endpoints that Home Assistant can query.

Example local API page:

```text
http://HOME_ASSISTANT_IP:3001/docs
```

Example API endpoint:

```text
http://HOME_ASSISTANT_IP:3001/households/
```

## Important notes

This add-on is a wrapper around the unofficial SureHub API project.

Do not expose this add-on directly to the internet.

Your Sure Petcare email and password are entered through the Home Assistant add-on configuration screen. They are not stored in this GitHub repository.

## Requirements

You need:

* Home Assistant OS or Home Assistant Supervised
* Home Assistant Supervisor / Apps / Add-ons support
* A Sure Petcare account
* A working Sure Petcare hub, feeder, flap, pet tag, or other supported Sure Petcare device
* Network access from Home Assistant to the internet

## Installation

### 1. Add the repository to Home Assistant

In Home Assistant, go to:

```text
Settings → Add-ons / Apps → Add-on Store
```

Open the three dot menu in the top right and choose:

```text
Repositories
```

Add this repository URL:

```text
https://github.com/ASTPlatinum/home-assistant-surehub-api-addon
```

Click **Add**.

### 2. Install the add-on

After adding the repository, reload the Add-on Store if needed.

Search for:

```text
SureHub API
```

Open the add-on and click:

```text
Install
```

### 3. Configure the add-on

Open the add-on configuration page and enter your Sure Petcare account details.

Example configuration:

```yaml
email: your_sure_petcare_email@example.com
password: your_sure_petcare_password
port: 3001
```

The default port is:

```text
3001
```

### 4. Start the add-on

Click:

```text
Start
```

Then open the add-on log.

A successful start should show something similar to:

```text
Uvicorn running on http://0.0.0.0:3001
```

## Testing the add-on

### API documentation page

Open this in a browser, replacing the IP address with your Home Assistant IP:

```text
http://HOME_ASSISTANT_IP:3001/docs
```

Example:

```text
http://10.0.6.249:3001/docs
```

If the add-on is working, you should see the SureHub API documentation page.

### Test household data

Open:

```text
http://HOME_ASSISTANT_IP:3001/households/
```

Example:

```text
http://10.0.6.249:3001/households/
```

If the credentials are correct, this should return JSON data showing your Sure Petcare household.

Make a note of your `household_id`, as it is needed for Home Assistant REST sensors.

## Useful endpoints

Replace `HOME_ASSISTANT_IP`, `HOUSEHOLD_ID`, `PET_ID`, and `DEVICE_ID` with your own values.

### Dashboard

```text
http://HOME_ASSISTANT_IP:3001/dashboard/
```

### Households

```text
http://HOME_ASSISTANT_IP:3001/households/
```

### Pets in a household

```text
http://HOME_ASSISTANT_IP:3001/households/HOUSEHOLD_ID/pets
```

### Devices in a household

```text
http://HOME_ASSISTANT_IP:3001/households/HOUSEHOLD_ID/devices
```

### Pet report

```text
http://HOME_ASSISTANT_IP:3001/households/HOUSEHOLD_ID/pets/PET_ID/report?from=YYYY-MM-DDT00:00:00Z&to=YYYY-MM-DDT23:59:59Z
```

Example:

```text
http://10.0.6.249:3001/households/193138/pets/752087/report?from=2026-05-14T00:00:00Z&to=2026-05-14T23:59:59Z
```

## Example Home Assistant sensors

The following example creates sensors for food eaten today by two cats.

Example details:

```text
Household ID: 193038
Dexter pet ID: 403076
Bhalu pet ID: 752007
```

Change these IDs to match your own household and pet IDs.

### REST sensors

If you use a separate `sensor.yaml` file included with:

```yaml
sensor: !include sensor.yaml
```

add this to `sensor.yaml`: Remember to change the household & pet ID's to suite.

```yaml
- platform: rest
  name: Dexter SureHub Feeding Report
  unique_id: dexter_surehub_feeding_report
  resource_template: "http://HOME_ASSISTANT_IP:3001/households/193038/pets/403076/report?from={{ now().strftime('%Y-%m-%dT00:00:00Z') }}&to={{ now().strftime('%Y-%m-%dT23:59:59Z') }}"
  scan_interval: 300
  value_template: "OK"
  json_attributes_path: "$.feeding"
  json_attributes:
    - datapoints

- platform: rest
  name: Bhalu SureHub Feeding Report
  unique_id: bhalu_surehub_feeding_report
  resource_template: "http://HOME_ASSISTANT_IP:3001/households/193038/pets/752007/report?from={{ now().strftime('%Y-%m-%dT00:00:00Z') }}&to={{ now().strftime('%Y-%m-%dT23:59:59Z') }}"
  scan_interval: 300
  value_template: "OK"
  json_attributes_path: "$.feeding"
  json_attributes:
    - datapoints
```

Replace:

```text
HOME_ASSISTANT_IP
```

with your Home Assistant IP address, for example:

```text
10.0.6.249
```

### Template sensors

If you use a separate `template_sensors.yaml` or `template.yaml` file included with:

```yaml
template: !include template_sensors.yaml
```

add this as a top-level template sensor block:

```yaml
- sensor:
    - name: Dexter Food Eaten Today
      unique_id: dexter_food_eaten_today
      unit_of_measurement: g
      state_class: total
      state: >
        {% set datapoints = state_attr('sensor.dexter_surehub_feeding_report', 'datapoints') or [] %}
        {% set ns = namespace(total=0) %}
        {% for point in datapoints %}
          {% for weight in point.weights %}
            {% if weight.change is defined and weight.change | float < 0 %}
              {% set ns.total = ns.total + ((weight.change | float) * -1) %}
            {% endif %}
          {% endfor %}
        {% endfor %}
        {{ ns.total | round(1) }}

    - name: Bhalu Food Eaten Today
      unique_id: bhalu_food_eaten_today
      unit_of_measurement: g
      state_class: total
      state: >
        {% set datapoints = state_attr('sensor.bhalu_surehub_feeding_report', 'datapoints') or [] %}
        {% set ns = namespace(total=0) %}
        {% for point in datapoints %}
          {% for weight in point.weights %}
            {% if weight.change is defined and weight.change | float < 0 %}
              {% set ns.total = ns.total + ((weight.change | float) * -1) %}
            {% endif %}
          {% endfor %}
        {% endfor %}
        {{ ns.total | round(1) }}
```

## How the food eaten calculation works

The SureHub report contains feeding datapoints. Each datapoint contains one or more bowl weight changes.

A negative `change` value means the food weight went down.

For example:

```yaml
change: -17
```

means approximately:

```text
17 g eaten
```

The template sensors sum all negative feeding changes for the day and convert them to positive gram values.

## Troubleshooting

### The docs page does not open

Check that the add-on is running.

Check the add-on log for:

```text
Uvicorn running on http://0.0.0.0:3001
```

Make sure you are using the correct Home Assistant IP address and port.

### `/households/` returns Internal Server Error

Check the add-on log.

Common causes:

* Incorrect Sure Petcare email
* Incorrect Sure Petcare password
* Sure Petcare cloud issue
* Add-on did not start correctly

### REST sensor shows `OK` but `datapoints: []`

The URL may be returning an empty report.

Use the full date/time format:

```text
from=YYYY-MM-DDT00:00:00Z&to=YYYY-MM-DDT23:59:59Z
```

instead of date only.

### Food eaten template shows `0.0`

Check the raw REST sensor first.

In Home Assistant, go to:

```text
Developer Tools → States
```

Search for:

```text
sensor.bhalu_surehub_feeding_report
```

The attributes should contain:

```yaml
datapoints:
  - from: ...
    weights:
      - change: -17
```

If `datapoints` is empty, the template sensor will also show `0.0`.

### Home Assistant cannot reach `127.0.0.1:3001`

Use the Home Assistant IP address instead:

```text
http://HOME_ASSISTANT_IP:3001
```

For example:

```text
http://10.0.6.249:3001
```

In Home Assistant, `127.0.0.1` may refer to the Home Assistant Core container rather than the add-on container.

## Security advice

Do not expose port `3001` to the internet.

Do not publish your Sure Petcare email or password in GitHub.

Do not paste your Sure Petcare password into issue reports, screenshots, or public logs.

Use this add-on only on your trusted local network.

## Credits

This add-on wraps the unofficial SureHub API project:

```text
https://github.com/fabieu/surehub-api
```

This repository only provides a Home Assistant add-on wrapper around that project.


## Indoor-only cat access

Version 0.2.0 adds local endpoints for changing an individual registered tag between normal access and indoor-only mode.

The add-on reuses the upstream SureHub API authentication and token handling. Home Assistant does not need to store a separate Sure Petcare token.

### Endpoints

Set a registered tag to indoor-only:

```text
POST /devices/{device_id}/tags/{tag_id}/indoor-only
```

Return a registered tag to normal access:

```text
POST /devices/{device_id}/tags/{tag_id}/normal
```

Sure Petcare currently uses profile `3` for indoor-only and profile `2` for normal access.

Example:

```bash
curl -X POST http://HOME_ASSISTANT_IP:3001/devices/DEVICE_ID/tags/TAG_ID/indoor-only
curl -X POST http://HOME_ASSISTANT_IP:3001/devices/DEVICE_ID/tags/TAG_ID/normal
```

After updating the add-on, these endpoints also appear in the Swagger documentation at:

```text
http://HOME_ASSISTANT_IP:3001/docs
```

### Home Assistant REST commands

```yaml
rest_command:
  cat_indoor_only:
    url: "http://HOME_ASSISTANT_IP:3001/devices/DEVICE_ID/tags/TAG_ID/indoor-only"
    method: POST

  cat_normal_access:
    url: "http://HOME_ASSISTANT_IP:3001/devices/DEVICE_ID/tags/TAG_ID/normal"
    method: POST
```

Do not expose port 3001 to the internet. These endpoints can change whether a registered pet is allowed to leave through the flap.


## Manual pet location

Version 0.3.0 adds convenience endpoints for manually setting a pet's Sure Petcare location.

Set a pet to inside:

```text
POST /pets/{pet_id}/inside
```

Set a pet to outside:

```text
POST /pets/{pet_id}/outside
```

These use the upstream SureHub pet state API. Sure Petcare represents inside as position `1` and outside as position `2`.

Example:

```bash
curl -X POST http://HOME_ASSISTANT_IP:3001/pets/PET_ID/inside
curl -X POST http://HOME_ASSISTANT_IP:3001/pets/PET_ID/outside
```

### Home Assistant REST commands

```yaml
rest_command:
  cat_location_inside:
    url: "http://HOME_ASSISTANT_IP:3001/pets/PET_ID/inside"
    method: POST

  cat_location_outside:
    url: "http://HOME_ASSISTANT_IP:3001/pets/PET_ID/outside"
    method: POST
```

These endpoints manually change the location recorded in Sure Petcare. They do not physically operate or lock the flap.


## Device battery levels

Version 0.3.2 adds a compact endpoint for device battery information:

```text
GET /batteries
```

Example:

```text
http://HOME_ASSISTANT_IP:3001/batteries
```

The response includes every Sure Petcare device with its name, device ID, product ID, serial number, online state, raw battery voltage, and estimated battery percentage. Devices without a battery are included with null battery values.

The percentage calculation follows the established surepy four-cell battery curve, using 1.2 V per cell as 0% and 1.6 V per cell as 100%, clamped to 0–100%.
