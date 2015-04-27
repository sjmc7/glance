# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

from glance.search.plugins import indexing_clients
from glance.search.plugins import base
from . import instances_notification_handler
from . import serialize_nova_server

CONF = cfg.CONF

class InstanceIndex(base.IndexBase):
    def __init__(self):
        super(InstanceIndex, self).__init__()

    def get_index_name(self):
        return 'nova'

    def get_document_type(self):
        return 'instance'

    def get_mapping(self):
        return {
            'dynamic': True,
            'properties': {
                'id': {'type': 'string', 'index': 'not_analyzed'},
                'instance_id': {'type': 'string', 'index': 'not_analyzed'},
                'name': {'type': 'string'},
                'name_not_analyzed': {'type': 'string', 'index': 'not_analyzed'},
                # TODO - make flavor flat?
                'flavor': {
                    'type': 'nested',
                    'properties': {
                        'id': {'type': 'string', 'index': 'not_analyzed'},
                        'name': {'type': 'string'},
                        'name_not_analyzed': {'type': 'string', 'index': 'not_analyzed'}
                    }
                },
                'owner': {'type': 'string', 'index': 'not_analyzed'},
                'tenant_id': {'type': 'string', 'index': 'not_analyzed'},
                'user_id': {'type': 'string', 'index': 'not_analyzed'},
                'created_at': {'type': 'date'},
                'updated_at': {'type': 'date'},
                'networks': {
                    'type': 'nested',
                    'properties': {
                        'name': {'type': 'string'},
                        'ipv4': {'type': 'ip'}
                    }
                },
                'image': {
                    'type': 'nested',
                    'properties': {
                        'id': {'type': 'string', 'index': 'not_analyzed'},
                        'name': {'type': 'string'},
                        'name_not_analyzed': {'type': 'string', 'index': 'not_analyzed'}
                    }
                },
                'availability_zone': {'type': 'string', 'index': 'not_analyzed'},
                'status': {'type': 'string', 'index': 'not_analyzed'},
            },
        }

    def get_facets(self):
        facets_disallowed = ('name_not_analyzed', 'image.name_not_analyzed',)
        facets_with_options = ('status', 'availability_zone', ('flavor.name', 'flavor.name_not_analyzed'))

        facets = super(InstanceIndex, self).get_facets()

        # Filter out undesirables
        facets = filter(lambda f: f['name'] not in facets_disallowed, facets)

        facet_terms = self.get_facet_terms(facets_with_options)

        for facet in facets:
            if facet['name'] in facet_terms:
                facet['options'] = facet_terms[facet['name']]

        return facets

    def get_rbac_filter(self, request_context):
        return [
            {
                "and": [
                    {
                        'term': {
                            'tenant_id': request_context.owner
                        }
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
        # TODO: paging etc
        return indexing_clients.get_novaclient().servers.list(
            limit=1000, 
            search_opts={'all_tenants': True}
        )

    def serialize(self, server):
        return serialize_nova_server(server)

    def get_notification_handler(self):
        return instances_notification_handler.InstanceHandler(
            self.engine,
            self.get_index_name(),
            self.get_document_type()
        )

    @staticmethod
    def get_notification_topic_exchanges():
        return (
            ('notifications', 'nova'),
            ('notifications', 'neutron')
        )

    def get_notification_supported_events(self):
        # TODO: DRY
        # Most events are duplicated by instance.update
        return [
            'compute.instance.update', 'compute.instance.exists',
            'compute.instance.create.end', 'compute.instance.delete.end',
            'compute.instance.power_on.end', 'compute.instance.power_off.end',
            'port.delete.end', 'port.create.end',
        ]
