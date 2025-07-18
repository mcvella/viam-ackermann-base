# Ackermann base Viam modular resource

This module implements the [rdk base API](https://github.com/rdk/base-api) in a mcvella:base:ackermann model.
With this model, you can configure wheeled bases that implement Ackermann steering to be controlled with the Viam app and Viam SDKs.

This model supports configurations of front, rear, and 4-wheel steering for vehicles that use servos for steering.
This model also supports configuration of multiple drive motors and an optional brake servo for automatic braking.

At the time of publishing, this has been tested with the [Danchee Ridgerock](https://www.redcatracing.com/products/danchee-ridgerock)

## Requirements

* A vehicle (wheeled base) that uses one or more drive [motor(s)](https://docs.viam.com/components/motor/), and one or two (front and/or rear) [servos](https://docs.viam.com/components/servo/) for steering.
* Optionally, a [servo](https://docs.viam.com/components/servo/) for braking.
* A [single board computer](https://docs.viam.com/components/board/) (SBC) like a Raspberry Pi 4 or OrangePi Zero 3 that is supported by Viam.

## Build and run

To use this module, follow the instructions to [add a module from the Viam Registry](https://docs.viam.com/registry/configure/#add-a-modular-resource-from-the-viam-registry) and select the `mcvella:base:ackermann` model from the [`mcvella:base:ackermann` module](https://app.viam.com/module/rdk/mcvella:base:ackermann).

## Configure your base

> [!NOTE]  
> Before configuring your base, you must [create a machine](https://docs.viam.com/manage/fleet/machines/#add-a-new-machine).

Navigate to the **Config** tab of your machine's page in [the Viam app](https://app.viam.com/).
Click on the **Components** subtab and click **Create component**.
Select the `base` type, then select the `mcvella:base:ackermann` model.
Click **Add module**, then enter a name for your base and click **Create**.

> [!NOTE]  
> For more information, see [Configure a Machine](https://docs.viam.com/manage/configuration/).

### Attributes

The following attributes are available for `rdk:base:mcvella:base:ackermann` bases:

| Name | Type | Inclusion | Description |
| ---- | ---- | --------- | ----------- |
| `drive_motors` | list | **Required** |  A list of configured drive motor names. |
| `steer_mode` | string | Optional |  The steering mode for the base: front, rear, or all, defaults to "front". |
| `wheelbase_mm` | float | **Required** |  The wheelbase measurement in mm. |
| `turning_radius_meters` | float | **Required** |  The turning radius in meters. |
| `max_speed_meters_per_second` | float | **Required** |  The max speed in meters per second. |
| `width_meters` | float | **Required** |  The width of the base in meters. |
| `wheel_circumference_meters` | float | **Required** |  The wheel circumference of the base in meters. |
| `steering_servo_front` | string | Optional |  The name of a configured servo, required if steer_mode is front or all. |
| `steering_servo_rear` | string | Optional |  The name of a configured servo, required if steer_mode is rear or all. |
| `neutral_servo_position` | integer | Optional |  The neutral (straight) position in degrees for the steering servos, default 90. |
| `min_servo_position` | integer | Optional |  The minimum position in degrees for the steering servos, default 0. |
| `max_servo_position` | integer | Optional |  The maximum position in degrees for the steering servos, default 180. |
| `brake_servo` | string | Optional |  The name of a configured servo for braking. |
| `brake_off_position` | integer | Optional |  The position in degrees for the brake servo when disengaged, default 0. |
| `brake_on_position` | integer | Optional |  The position in degrees for the brake servo when engaged, default 90. |

### Brake Servo Functionality

When a `brake_servo` is configured, the base will automatically:

- **Disengage the brake** (move to `brake_off_position`) when movement starts via `set_power()`, `set_velocity()`, or `move_straight()`
- **Engage the brake** (move to `brake_on_position`) when `stop()` is called or when power/velocity is set to zero
- **Engage the brake** after completing a `move_straight()` operation

This provides automatic braking functionality to prevent the vehicle from rolling when stopped.

### Example configuration

```json
{
  "drive_motors": [ "front_motor", "rear_motor" ],
  "steer_mode": "front",
  "steering_servo_front": "servo1",
  "wheelbase_mm": 320,
  "turning_radius_meters": 0.8,
  "max_speed_meters_per_second": 0.75,
  "width_meters": 0.25,
  "wheel_circumference_meters": 0.3,
  "brake_servo": "brake_servo1",
  "brake_off_position": 0,
  "brake_on_position": 90
}
```
