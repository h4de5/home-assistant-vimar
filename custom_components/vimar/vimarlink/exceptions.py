"""Vimar API Exception classes."""

from __future__ import annotations


class VimarApiError(Exception):
    """Vimar API General Exception."""

    err_args = []

    def __init__(self, *args, **kwargs):
        """Init a default Vimar api exception."""
        self.err_args = args
        super().__init__(*args)

    def __str__(self):
        """Stringify exception text."""
        return f"{self.__class__.__name__}: {self.err_args[0]}" % self.err_args[1:]


class VimarConfigError(VimarApiError):
    """Vimar API Configuration Exception."""

    pass


class VimarConnectionError(VimarApiError):
    """Vimar API Connection Exception."""

    pass
