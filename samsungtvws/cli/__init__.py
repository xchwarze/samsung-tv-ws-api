from .main import cli

from . import apps as _apps  # noqa: F401
from . import remote as _remote  # noqa: F401
from . import rest as _rest  # noqa: F401
from . import shortcuts as _shortcuts  # noqa: F401
from . import art as _art  # noqa: F401
from . import wol as _wol  # noqa: F401

__all__ = ["cli"]
