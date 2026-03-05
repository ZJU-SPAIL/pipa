"""Backward-compatible shim for the legacy ``pipa.main`` module."""

from pipa.commands.main import PipaCLI, main

__all__ = ["PipaCLI", "main"]
