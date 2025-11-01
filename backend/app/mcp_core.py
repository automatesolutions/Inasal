"""Modular Code Platform - reusable backend logic blocks"""

from typing import Any, Callable, Dict, Optional


class MCPModule:
    """Base class for MCP modules"""

    def __init__(self, name: str):
        self.name = name
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, action: str, handler: Callable):
        """Register a handler for a specific action"""
        self.handlers[action] = handler

    async def execute(self, action: str, **kwargs) -> Any:
        """Execute a registered handler"""
        if action not in self.handlers:
            raise ValueError(f"Unknown action: {action}")

        handler = self.handlers[action]
        import asyncio
        if asyncio.iscoroutinefunction(handler):
            return await handler(**kwargs)
        return handler(**kwargs)


class MCPRegistry:
    """Registry for MCP modules"""

    def __init__(self):
        self.modules: Dict[str, MCPModule] = {}

    def register_module(self, module: MCPModule):
        """Register an MCP module"""
        self.modules[module.name] = module

    async def call(self, module_name: str, action: str, **kwargs) -> Any:
        """Call an action on a registered module"""
        if module_name not in self.modules:
            raise ValueError(f"Unknown module: {module_name}")

        module = self.modules[module_name]
        return await module.execute(action, **kwargs)


# Global registry instance
registry = MCPRegistry()


# Example usage modules
class DestinationModule(MCPModule):
    """Module for destination-related operations"""

    def __init__(self):
        super().__init__("destination")

        self.register_handler("search", self.search_destinations)
        self.register_handler("details", self.get_details)

    async def search_destinations(self, query: str, filters: Optional[Dict] = None):
        """Search for destinations"""
        # TODO: Implement destination search
        return []

    async def get_details(self, destination_id: str):
        """Get destination details"""
        # TODO: Implement destination details retrieval
        return {}


# Initialize default modules
destination_module = DestinationModule()
registry.register_module(destination_module)

