from __future__ import annotations

from typing import TypeVar, Generic, Optional, Union

import firefly.domain as ffd

from .crud_operation import CrudOperation
from ..core.service import Service
from ..messaging.system_bus import SystemBusAware
from ...value_object.generic_base import GenericBase

T = TypeVar('T')


class UpdateEntity(Generic[T], Service, GenericBase, CrudOperation, SystemBusAware):
    _registry: ffd.Registry = None

    def __call__(self, **kwargs) -> Optional[Union[ffd.Message, object]]:
        type_ = self._type()
        id_arg = type_.match_id_from_argument_list(kwargs)
        entity = self._registry(type_).find(list(id_arg.values()).pop())
        for k, v in kwargs.items():
            if hasattr(entity, k):
                setattr(entity, k, v)
        self._registry(type_).update(entity)
        self.dispatch(self._build_event(type_, 'update'))

        return entity