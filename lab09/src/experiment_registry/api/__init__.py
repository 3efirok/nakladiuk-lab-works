"""REST API package.

`experiment_registry.api:app` is created lazily on first access, so importing schemas or
the client does not open a database connection.
"""

from typing import Any

__all__ = ["app"]


def __getattr__(name: str) -> Any:
    if name == "app":
        from experiment_registry.api.app import create_app

        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
