"""Exceptions raised by the parameter package."""

from __future__ import annotations


class ParameterError(ValueError):
    """Invalid parameter data, optionally located by a dotted key path."""

    def __init__(self, message: str, path: str = "") -> None:
        self.message = message
        self.path = path
        super().__init__(f"{path}: {message}" if path else message)

    def with_parent(self, key: str) -> ParameterError:
        """Return a copy of this error located one level further up the tree."""
        path = f"{key}.{self.path}" if self.path else key
        return type(self)(self.message, path)


class UnitError(ParameterError):
    """A units expression could not be parsed."""
