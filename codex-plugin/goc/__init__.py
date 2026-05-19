"""Game of Cards — XP-style story-card kanban methodology framework.

Distribution name on PyPI: `game-of-cards`.
Import name + console script: `goc` (the pyyaml pattern).
"""

__version__ = "0.0.20"

try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
except ImportError:
    pass
else:
    try:
        __version__ = _pkg_version("game-of-cards")
    except PackageNotFoundError:
        pass
