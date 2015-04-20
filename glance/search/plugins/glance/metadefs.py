# Copyright 2015 Intel Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy

import six

import glance.db
from glance.db.sqlalchemy import models_metadef as models
from glance.search.plugins import base
from glance.search.plugins import indexing_clients
from glance.search.plugins import metadefs_notification_handler
from . import serialize_glance_metadef


class MetadefIndex(base.IndexBase):
    def __init__(self):
        super(MetadefIndex, self).__init__()

        self.db_api = glance.db.get_api()

    def get_index_name(self):
        return 'glance'

    def get_document_type(self):
        return 'metadef'

    def get_mapping(self):
        property_mapping = {
            'dynamic': True,
            'type': 'nested',
            'properties': {
                'property': {'type': 'string', 'index': 'not_analyzed'},
                'type': {'type': 'string'},
                'title': {'type': 'string'},
                'description': {'type': 'string'},
            }
        }
        mapping = {
            '_id': {
                'path': 'namespace',
            },
            'properties': {
                'display_name': {'type': 'string'},
                'description': {'type': 'string'},
                'namespace': {'type': 'string', 'index': 'not_analyzed'},
                'owner': {'type': 'string', 'index': 'not_analyzed'},
                'visibility': {'type': 'string', 'index': 'not_analyzed'},
                'resource_types': {
                    'type': 'nested',
                    'properties': {
                        'name': {'type': 'string'},
                        'prefix': {'type': 'string'},
                        'properties_target': {'type': 'string'},
                    },
                },
                'objects': {
                    'type': 'nested',
                    'properties': {
                        'id': {'type': 'string', 'index': 'not_analyzed'},
                        'name': {'type': 'string'},
                        'description': {'type': 'string'},
                        'properties': property_mapping,
                    }
                },
                'properties': property_mapping,
                'tags': {
                    'type': 'nested',
                    'properties': {
                        'name': {'type': 'string'},
                    }
                }
            },
        }
        return mapping

    def get_rbac_filter(self, request_context):
        # TODO(krykowski): Define base get_rbac_filter in IndexBase class
        # which will provide some common subset of query pieces.
        # Something like:
        # def get_common_context_pieces(self, request_context):
        # return [{'term': {'owner': request_context.owner,
        #                  'type': {'value': self.get_document_type()}}]
        return [
            {
                "and": [
                    {
                        'or': [
                            {
                                'term': {
                                    'owner': request_context.owner
                                }
                            },
                            {
                                'term': {
                                    'visibility': 'public'
                                }
                            }
                        ]
                    },
                    {
                        'type': {
                            'value': self.get_document_type()
                        }
                    }
                ]
            }
        ]

    def get_objects(self):
        return list(indexing_clients.get_glanceclient().metadefs_namespace.list())

    def get_notification_handler(self):
        return metadefs_notification_handler.MetadefHandler(
            self.engine,
            self.get_index_name(),
            self.get_document_type()
        )

    def get_notification_supported_events(self):
        return [
            "metadef_namespace.create",
            "metadef_namespace.update",
            "metadef_namespace.delete",
            "metadef_object.create",
            "metadef_object.update",
            "metadef_object.delete",
            "metadef_property.create",
            "metadef_property.update",
            "metadef_property.delete",
            "metadef_tag.create",
            "metadef_tag.update",
            "metadef_tag.delete",
            "metadef_resource_type.create",
            "metadef_resource_type.delete",
            "metadef_namespace.delete_properties",
            "metadef_namespace.delete_objects",
            "metadef_namespace.delete_tags"
        ]
