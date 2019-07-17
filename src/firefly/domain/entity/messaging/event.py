from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field

from .message import Message


@dataclass
class Event(Message, ABC):
    source_context: str = field(default=None, init=False)

    def __post_init__(self):
        self.source_context = self.__module__.split('.')[0]

    def __str__(self):
        return '{}.{}'.format(self.source_context,
                              self.__class__.__name__) if self.source_context is not None else self.__class__.__name__

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, str) and other == str(self):
            return True
        try:
            return isinstance(self, other)
        except TypeError:
            return False
