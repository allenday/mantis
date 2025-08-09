"""
Mantis Service Layer

Provides JSON-RPC and other service implementations for the Mantis system.
Primary focus on A2A protocol compliance through JSON-RPC.
"""

from .jsonrpc_service import MantisJSONRPCService, serve_jsonrpc, create_app

__all__ = ["MantisJSONRPCService", "serve_jsonrpc", "create_app"]