#  Copyright (c) 2019 JD Williams
#
#  This file is part of Firefly, a Python SOA framework built by JD Williams. Firefly is free software; you can
#  redistribute it and/or modify it under the terms of the GNU General Public License as published by the
#  Free Software Foundation; either version 3 of the License, or (at your option) any later version.
#
#  Firefly is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
#  implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#  Public License for more details. You should have received a copy of the GNU Lesser General Public
#  License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  You should have received a copy of the GNU General Public License along with Firefly. If not, see
#  <http://www.gnu.org/licenses/>.

from __future__ import annotations

import logging
import traceback
from typing import Union

import firefly.domain as ffd


class PythonLogger(ffd.Logger):
    def __init__(self):
        self.log = logging
        self.set_level_to_warning()

    def debug(self, message: str, *args, **kwargs):
        self.log.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self.log.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self.log.warning(message, *args, **kwargs)

    def error(self, message: Union[str, Exception], *args, **kwargs):
        if isinstance(message, Exception):
            message = '\r'.join([str(message)] + traceback.format_exception(None, message, message.__traceback__))
        self.log.error(message, *args, **kwargs)

    def set_level_to_fatal(self):
        self.log.getLogger().setLevel(logging.FATAL)

    def set_level_to_error(self):
        self.log.getLogger().setLevel(logging.ERROR)

    def set_level_to_warning(self):
        self.log.getLogger().setLevel(logging.WARNING)

    def set_level_to_info(self):
        self.log.getLogger().setLevel(logging.INFO)

    def set_level_to_debug(self):
        self.log.getLogger().setLevel(logging.DEBUG)

    def disable(self):
        self.log.getLogger().setLevel(logging.NOTSET)
