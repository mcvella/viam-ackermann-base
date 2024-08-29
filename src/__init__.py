"""
This file registers the model with the Python SDK.
"""

from viam.components.base import Base
from viam.resource.registry import Registry, ResourceCreatorRegistration

from .ackermann import ackermann

Registry.register_resource_creator(Base.SUBTYPE, ackermann.MODEL, ResourceCreatorRegistration(ackermann.new, ackermann.validate))
