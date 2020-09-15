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

import inspect
from abc import ABC, abstractmethod
from dataclasses import fields
from datetime import datetime
from typing import Type, get_type_hints, List, Union, Callable, Dict, Tuple

import firefly.domain as ffd
import inflection
# noinspection PyDataclass
from jinjasql import JinjaSql

from .rdb_repository import Index, Column


# noinspection PyDataclass
class RdbStorageInterface(ffd.LoggerAware, ABC):
    _serializer: ffd.Serializer = None
    _j: JinjaSql = None
    _cache: dict = {}
    _sql_prefix = 'sql'
    _map_indexes = False
    _map_all = False
    _identifier_quote_char = '"'

    def __init__(self, **kwargs):
        self._tables_checked = []

    def disconnect(self):
        self._disconnect()

    def _disconnect(self):
        pass

    def add(self, entity: ffd.Entity):
        self._check_prerequisites(entity.__class__)
        self._add(entity)

    @abstractmethod
    def _add(self, entity: ffd.Entity):
        pass

    def all(self, entity_type: Type[ffd.Entity], criteria: ffd.BinaryOp = None, limit: int = None, offset: int = None,
            sort: Tuple[Union[str, Tuple[str, bool]]] = None, raw: bool = False, count: bool = False):
        self._check_prerequisites(entity_type)
        return self._all(entity_type, criteria, limit, offset, raw=raw, count=count, sort=sort)

    @abstractmethod
    def _all(self, entity_type: Type[ffd.Entity], criteria: ffd.BinaryOp = None, limit: int = None, offset: int = None,
             sort: Tuple[Union[str, Tuple[str, bool]]] = None, raw: bool = False, count: bool = False):
        pass

    def find(self, uuid: str, entity_type: Type[ffd.Entity]):
        self._check_prerequisites(entity_type)
        return self._find(uuid, entity_type)

    @abstractmethod
    def _find(self, uuid: str, entity_type: Type[ffd.Entity]):
        pass

    def remove(self, entity: Union[ffd.Entity, Callable], force: bool = False):
        self._check_prerequisites(entity.__class__)
        if hasattr(entity, 'deleted_on') and not force:
            entity.deleted_on = datetime.now()
            self._update(entity)
        else:
            self._remove(entity)

    @abstractmethod
    def _remove(self, entity: Union[ffd.Entity, Callable]):
        pass

    def update(self, entity: ffd.Entity):
        self._check_prerequisites(entity.__class__)
        if hasattr(entity, 'updated_on'):
            entity.updated_on = datetime.now()
        self._update(entity)

    @abstractmethod
    def _update(self, entity: ffd.Entity):
        pass

    @abstractmethod
    def _ensure_connected(self):
        pass

    def clear(self, entity: Type[ffd.Entity]):
        self.execute(*self._generate_query(entity, f'{self._sql_prefix}/truncate_table.sql'))

    def destroy(self, entity: Type[ffd.Entity]):
        self.execute(*self._generate_query(entity, f'{self._sql_prefix}/drop_table.sql'))

    @staticmethod
    def _fqtn(entity: Type[ffd.Entity]):
        return inflection.tableize(entity.get_fqn())

    def _check_prerequisites(self, entity: Type[ffd.Entity]):
        self._ensure_connected()

    def get_entity_columns(self, entity: Type[ffd.Entity]):
        ret = []
        annotations_ = get_type_hints(entity)
        for f in fields(entity):
            if f.name.startswith('_'):
                continue

            c = Column(
                name=f.name,
                type=annotations_[f.name],
                length=f.metadata.get('length', None),
                is_id=f.metadata.get('id', False)
            )
            if self._map_all is True:
                ret.append(c)
            elif self._map_indexes and 'index' in f.metadata:
                ret.append(c)
            elif 'id' in f.metadata:
                ret.append(c)

        if not self._map_all:
            ret.insert(1, Column(name='document', type='str'))

        return ret

    def get_table_columns(self, entity: Type[ffd.Entity]):
        return self._get_table_columns(entity)

    @abstractmethod
    def _get_table_columns(self, entity: Type[ffd.Entity]):
        pass

    def add_column(self, entity: Type[ffd.Entity], column: Column):
        self.execute(
            *self._generate_query(entity, f'{self._sql_prefix}/add_column.sql', {'column': column})
        )

    def drop_column(self, entity: Type[ffd.Entity], column: Column):
        self.execute(
            *self._generate_query(entity, f'{self._sql_prefix}/drop_column.sql', {'column': column})
        )

    def get_entity_indexes(self, entity: Type[ffd.Entity]):
        ret = []
        table = self._fqtn(entity).replace('.', '_')
        for field_ in fields(entity):
            if 'index' in field_.metadata:
                if field_.metadata['index'] is True:
                    ret.append(
                        Index(table=table, columns=[field_.name], unique=field_.metadata.get('unique', False) is True)
                    )
                elif isinstance(field_.metadata['index'], str):
                    name = field_.metadata['index']
                    idx = next(filter(lambda i: i.name == name, ret))
                    if not idx:
                        ret.append(Index(table=table, columns=[field_.name],
                                         unique=field_.metadata.get('unique', False) is True))
                    else:
                        idx.columns.append(field_.name)
                        if field_.metadata.get('unique', False) is True and idx.unique is False:
                            idx.unique = True

        return ret

    def get_table_indexes(self, entity: Type[ffd.Entity]):
        return self._get_table_indexes(entity)

    @abstractmethod
    def _get_table_indexes(self, entity: Type[ffd.Entity]):
        pass

    def create_index(self, entity: Type[ffd.Entity], index: Index):
        self.execute(
            *self._generate_query(entity, f'{self._sql_prefix}/add_index.sql', {'index': index})
        )

    def drop_index(self, entity: Type[ffd.Entity], index: Index):
        self.execute(
            *self._generate_query(entity, f'{self._sql_prefix}/drop_index.sql', {'index': index})
        )

    @abstractmethod
    def _build_entity(self, entity: Type[ffd.Entity], data, raw: bool = False):
        pass

    @staticmethod
    def _generate_index(name: str):
        return ''

    def execute(self, sql: str, params: dict = None):
        self._execute(sql, params)

    @abstractmethod
    def _execute(self, sql: str, params: dict = None):
        pass

    def _generate_query(self, entity: Union[ffd.Entity, Type[ffd.Entity]], template: str, params: dict = None):
        params = params or {}
        if not inspect.isclass(entity):
            entity = entity.__class__

        def mapped_fields(e):
            return self.get_entity_columns(e)

        template = self._j.env.select_template([template, '/'.join(['sql', template.split('/')[1]])])
        data = {
            'fqtn': self._fqtn(entity),
            '_q': self._identifier_quote_char,
            'map_indexes': self._map_indexes,
            'map_all': self._map_all,
            'mapped_fields': mapped_fields,
        }
        data.update(params)
        sql, params = self._j.prepare_query(template, data)

        return " ".join(sql.split()), params

    def create_table(self, entity_type: Type[ffd.Entity]):
        self.execute(
            *self._generate_query(
                entity_type,
                f'{self._sql_prefix}/create_table.sql',
                {'entity': entity_type, }
            )
        )

    def create_database(self, entity_type: Type[ffd.Entity]):
        self.execute(
            *self._generate_query(
                entity_type,
                f'{self._sql_prefix}/create_database.sql',
                {'context_name': entity_type.get_class_context()}
            )
        )

    def _data_fields(self, entity: ffd.Entity):
        ret = {}
        for f in self.get_entity_columns(entity.__class__):
            if f.name == 'document' and not hasattr(entity, 'document'):
                ret[f.name] = self._serialize_entity(entity)
            elif inspect.isclass(f.type) and issubclass(f.type, ffd.AggregateRoot):
                ret[f.name] = getattr(entity, f.name).id_value()
            elif ffd.is_type_hint(f.type):
                origin = ffd.get_origin(f.type)
                args = ffd.get_args(f.type)
                if origin is List:
                    if issubclass(args[0], ffd.AggregateRoot):
                        ret[f.name] = self._serializer.serialize(
                            list(map(lambda e: e.id_value(), getattr(entity, f.name)))
                        )
                    else:
                        ret[f.name] = self._serializer.serialize(getattr(entity, f.name))
                elif origin is Dict:
                    if issubclass(args[1], ffd.AggregateRoot):
                        ret[f.name] = {k: v.id_value() for k, v in getattr(entity, f.name).items()}
                    else:
                        ret[f.name] = self._serializer.serialize(getattr(entity, f.name))
            elif f.type is list or f.type is dict:
                ret[f.name] = self._serializer.serialize(getattr(entity, f.name))
            else:
                ret[f.name] = getattr(entity, f.name)
                if isinstance(ret[f.name], ffd.ValueObject):
                    ret[f.name] = self._serializer.serialize(ret[f.name])
        return ret

    def _select_list(self, entity: Type[ffd.Entity]):
        if self._map_all:
            return list(map(lambda c: c.name, self.get_entity_columns(entity)))
        return ['document']

    def _get_relationships(self, entity: Type[ffd.Entity]):
        relationships = {}
        annotations_ = get_type_hints(entity)
        for k, v in annotations_.items():
            if k.startswith('_'):
                continue
            if isinstance(v, type) and issubclass(v, ffd.AggregateRoot):
                relationships[k] = {
                    'field_name': k,
                    'target': v,
                    'this_side': 'one',
                }
            elif ffd.is_type_hint(v):
                origin = ffd.get_origin(v)
                args = ffd.get_args(v)
                if origin is List and issubclass(args[0], ffd.AggregateRoot):
                    relationships[k] = {
                        'field_name': k,
                        'target': args[0],
                        'this_side': 'many',
                    }
        return relationships

    def _get_relationship(self, entity: Type[ffd.Entity], inverse_entity: Type[ffd.Entity]):
        relationships = self._get_relationships(entity)
        for k, v in relationships.items():
            if v['target'] == inverse_entity:
                return v

    def _serialize_entity(self, entity: ffd.Entity):
        relationships = self._get_relationships(entity.__class__)
        if len(relationships.keys()) > 0:
            obj = entity.to_dict(force_all=True, skip=list(relationships.keys()))
            for k, v in relationships.items():
                if v['this_side'] == 'one':
                    obj[k] = getattr(entity, k).id_value()
                elif v['this_side'] == 'many':
                    obj[k] = list(map(lambda kk: kk.id_value(), getattr(entity, k)))
        else:
            obj = entity.to_dict(force_all=True)

        return self._serializer.serialize(obj)
