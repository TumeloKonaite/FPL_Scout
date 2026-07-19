from __future__ import annotations

from collections.abc import Callable


_reload: Callable[[], None] | None = None
_commit: Callable[[], None] | None = None


def configure_runtime_volume(
    *,
    reload: Callable[[], None] | None = None,
    commit: Callable[[], None] | None = None,
) -> None:
    """Install Modal Volume hooks without coupling local code to Modal."""
    global _reload, _commit
    _reload = reload
    _commit = commit


def reload_runtime_volume() -> None:
    if _reload is not None:
        _reload()


def commit_runtime_volume() -> None:
    if _commit is not None:
        _commit()

