from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, Tuple, Final, List, cast
from typing_extensions import Self

from viam.module.types import Reconfigurable
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, Vector3
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily

from viam.components.base import Base
from viam.components.servo import Servo
from viam.components.motor import Motor

from viam.logging import getLogger

import time
import asyncio
import math

LOGGER = getLogger(__name__)

class ackermann(Base, Reconfigurable):
    
    """
    Base represents a physical base of a robot.
    """
    class Properties:
        wheelbase_mm: float
        turning_radius_meters: float
        max_speed_meters_per_second: float
        width_meters: float
        wheel_circumference_meters: float

    MODEL: ClassVar[Model] = Model(ModelFamily("mcvella", "base"), "ackermann")
    
    properties: Properties
    steer_mode: str = ""
    motors: List[Motor] = []
    front_servo: Servo
    rear_servo: Servo
    has_front_servo: bool
    has_rear_servo: bool
    neutral_servo_position: int
    max_servo_position: int
    min_servo_position: int

    # Constructor
    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        my_class = cls(config.name)
        my_class.reconfigure(config, dependencies)
        return my_class

    # Validates JSON Configuration
    @classmethod
    def validate(cls, config: ComponentConfig):
        wheelbase_mm = config.attributes.fields["wheelbase_mm"].number_value or 0
        if wheelbase_mm == 0:
            raise Exception("A wheelbase_mm must be defined")
        turning_radius_meters = config.attributes.fields["turning_radius_meters"].number_value or 0
        if turning_radius_meters == 0:
            raise Exception("A turning_radius_meters must be defined")
        max_speed_meters_per_second = config.attributes.fields["max_speed_meters_per_second"].number_value or 0
        if max_speed_meters_per_second == 0:
            raise Exception("A width_meters must be defined")
        width_meters = config.attributes.fields["width_meters"].number_value or 0
        if width_meters == 0:
            raise Exception("A width_meters must be defined")
        wheel_circumference_meters = config.attributes.fields["wheel_circumference_meters"].number_value or 0
        if wheel_circumference_meters == 0:
            raise Exception("A wheel_circumference_meters must be defined")
                
        deps = []
        motors = config.attributes.fields["drive_motors"].list_value or []
        if len(motors) == 0:
            raise Exception("At least one motor component name must be defined in a drive_motors array")
        
        for m in motors:
            deps.append(m)

        steering_mode = config.attributes.fields["drive_mode"].string_value or "front"

        steering_servo_front = config.attributes.fields["steering_servo_front"].string_value
        if steering_servo_front == "" and steering_mode != "rear":
            raise Exception("steering_servo_front must be defined unless steering_mode is 'rear'")
        if steering_servo_front != "":
            deps.append(steering_servo_front)

        steering_servo_rear = config.attributes.fields["steering_servo_rear"].string_value
        if steering_servo_rear == "" and (steering_mode == "rear" or steering_mode == 'all'):
            raise Exception("steering_servo_rear must be defined unless steering_mode is 'front'")
        if steering_servo_rear != "":
            deps.append(steering_servo_rear)

        LOGGER.info(deps)
        return deps

    # Handles attribute reconfiguration
    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        self.properties = self.Properties()
        self.properties.wheelbase_mm = config.attributes.fields["wheelbase_mm"].number_value
        self.properties.turning_radius_meters = config.attributes.fields["turning_radius_meters"].number_value 
        self.properties.max_speed_meters_per_second = config.attributes.fields["max_speed_meters_per_second"].number_value
        self.properties.width_meters = config.attributes.fields["width_meters"].number_value 
        self.properties.wheel_circumference_meters = config.attributes.fields["wheel_circumference_meters"].number_value 

        self.steer_mode = config.attributes.fields["steer_mode"].string_value or "front"
        self.neutral_servo_position = config.attributes.fields["neutral_servo_position"].number_value or 90
        self.max_servo_position = config.attributes.fields["max_servo_position"].number_value or 180
        self.min_servo_position = config.attributes.fields["min_servo_position"].number_value or 0

        LOGGER.info(dependencies)
        motors = config.attributes.fields["drive_motors"].list_value
        for m in motors:
            actual_motor = dependencies[Motor.get_resource_name(m)]
            motor = cast(Motor, actual_motor)
            self.motors.append(motor)
        
        front_servo = config.attributes.fields["steering_servo_front"].string_value or ""
        if front_servo != "":
            actual_front_servo = dependencies[Servo.get_resource_name(front_servo)]
            self.front_servo = cast(Servo, actual_front_servo)
            self.has_front_servo = True
        else:
            self.has_front_servo = False
        
        rear_servo = config.attributes.fields["steering_servo_rear"].string_value or ""
        if rear_servo != "":
            actual_rear_servo = dependencies[Servo.get_resource_name(rear_servo)]
            self.rear_servo = cast(Servo, actual_rear_servo)
            self.has_rear_servo = True
        else:
            self.has_rear_servo = False

        return
    
    async def move_straight(
        self,
        distance: int,
        velocity: float,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        LOGGER.info( f"received a MoveStraight with distance {distance}, velocity {velocity}")
        if velocity / 1000 > self.properties.max_speed_meters_per_second:
            return f"requested speed {velocity}/1000 is greater than maximum base speed {self.properties.max_speed_meters_per_second}"
        if velocity == 0:
            return "cannot move base straight at 0 mm per sec"
        
        # move steering to neutral position
        await self.do_steer(0)

        drive_sec = distance / velocity
        drive_power = (velocity/1000) / self.properties.max_speed_meters_per_second

        drive_tasks = []
        for m in self.motors:
            drive_tasks.append(asyncio.create_task(m.set_power(drive_power)))
        await asyncio.gather(*drive_tasks)
    
        await asyncio.sleep(drive_sec)
        await self.stop()

    async def do_steer(self, position: int):
        primary_servo = self.front_servo
        secondary_servo = ""

        angle = int(self.servo_angle(position))
        secondary_angle = int(self.servo_angle(-position))

        if self.has_rear_servo:
            secondary_servo  = self.rear_servo
        if self.steer_mode == "rear":
            primary_servo = self.rear_servo
            angle = int(self.servo_angle(-position))
            secondary_angle = int(self.servo_angle(position))

            if self.has_front_servo:
                secondary_servo = self.front_servo
        
        await primary_servo.move(angle)

        if self.steer_mode == 'all':
            await secondary_servo.move(secondary_angle)
        else:
            if secondary_servo != "":
                secondary_angle = int(self.servo_angle(0))
                await secondary_servo.move(secondary_angle)
        
        return
    
    def servo_angle(self, val: float):
        if val > 1:
            val = 1
        if val < -1:
            val = -1
	
        angle_from_neutral = val * (self.max_servo_position - self.neutral_servo_position)
        return int(self.neutral_servo_position + angle_from_neutral)
    
    def wheel_angle(self, turn_radius_m: float):
        return math.cos(math.radians(math.atan2(
		    math.sqrt(math.pow(self.properties.wheelbase_mm, 2) / (math.pow(turn_radius_m * 1000, 2) - math.pow(self.properties.wheelbase_mm, 2))),
		    self.properties.wheelbase_mm)))
    
    async def spin(
        self,
        angle: float,
        velocity: float,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        return "ackermann steering does not support spin"

    async def set_power(
        self,
        linear: Vector3,
        angular: Vector3,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        LOGGER.info(f"received a set_power with linear.X: {linear.x}, linear.Y: {linear.y} linear.Z: {linear.z}, angular.X: {angular.x}, angular.Y: {angular.y}, angular.Z: {angular.z}")
        await self.do_steer(angular.z)
        drive_tasks = []
        for m in self.motors:
            drive_tasks.append(asyncio.create_task(m.set_power(linear.y)))
        await asyncio.gather(*drive_tasks)
        
    async def set_velocity(
        self,
        linear: Vector3,
        angular: Vector3,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        # TODO - account for differing turning radius in different steer modes
        
        LOGGER.info(f"received a set_velocity with linear.X: {linear.x}, linear.Y: {linear.y} linear.Z: {linear.z}, angular.X: {angular.x}, angular.Y: {angular.y}, angular.Z: {angular.z}")

        if linear.y / 1000 > self.properties.max_speed_meters_per_second:
            return f"requested speed {linear.y} is greater than maximum base speed {self.properties.max_speed_meters_per_second}"

        max_angle_velocity_rad = (linear.y / 1000) / self.properties.turning_radius_meters
        max_degs = abs(math.cos(math.radians(max_angle_velocity_rad)))
        if max_degs < abs(angular.z):
            max_degs = abs(math.cos(math.radians(max_angle_velocity_rad)))
            return f"at requested speed of {linear.y} mm/s, a base with turning radius {self.properties.turning_radius_meters} m can turn at most {max_degs} degrees per second"
        	
        if angular.z != 0:
		    # If we are here then requested lin/ang velocities are valid
		    # Took this "fancy math" from https://github.com/viam-labs/ackermann-pwm-base/blob/main/pwmbase/base.go
            desired_turn_rad = abs(linear.y / 1000) / math.cos(math.radians(abs(angular.z)))
            turn_angle = math.copysign(self.wheel_angle(desired_turn_rad), angular.z)

            if linear.y < 0:
                turn_angle *= -1
            
            await self.do_steer(turn_angle / self.max_servo_position)
        else:
            await self.do_steer(0)

        drive_tasks = []
        for m in self.motors:
            drive_tasks.append(asyncio.create_task(m.set_power((linear.y / 1000) / self.properties.max_speed_meters_per_second)))
        await asyncio.gather(*drive_tasks)
    
    async def stop(
        self,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        stop_tasks = []
        for m in self.motors:
            stop_tasks.append(asyncio.create_task(m.stop()))
    
        await asyncio.gather(*stop_tasks)
    
    async def is_moving(self) -> bool:
        tasks = []
        for m in self.motors:
            tasks.append(asyncio.create_task(m.is_moving()))
    
        results = await asyncio.gather(*tasks)
        for r in results:
            if r == True:
                return True
    
        return False
        
    async def get_properties(self, *, timeout: Optional[float] = None, **kwargs) -> Properties:
        return self.properties

