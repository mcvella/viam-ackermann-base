import asyncio
import sys

from viam.module.module import Module
from viam.components.base import Base
from viam.resource.registry import Registry, ResourceCreatorRegistration

from src.ackermann import ackermann


async def main():
    """This function creates and starts a new module, after adding all desired resources.
    Resources must be pre-registered. For an example, see the `__init__.py` file.
    """
    Registry.register_resource_creator(Base.API, ackermann.MODEL, ResourceCreatorRegistration(ackermann.new, ackermann.validate))

    module = Module.from_args()
    module.add_model_from_registry(Base.API, ackermann.MODEL)
    await module.start()

if __name__ == "__main__":
    asyncio.run(main())
