from __future__ import annotations

from dataclasses import dataclass

from .message import Message


@dataclass
class Command(Message):
    pass
