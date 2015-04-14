# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
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
from novaclient.v2 import client as nc_client

from glance.search.plugins import base
from . import instances_notification_handler

CONF = cfg.CONF


class InstanceIndex(base.IndexBase):
    def __init__(self):
        super(InstanceIndex, self).__init__()

        self._instance_base_properties = [
            'id', 'name', 'status', 'power_state', 'owner'
        ]

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
                # TODO - make flavor flat?
                'flavor': {
                    'type': 'nested',
                    'properties': {
                        'id': {'type': 'string', 'index': 'not_analyzed'},
                        'name': {'type': 'string', 'index': 'not_analyzed'},
                        }
                },
                'owner': {'type': 'string', 'index': 'not_analyzed'},
                'created_at': {'type': 'date'},
                'updated_at': {'type': 'date'},
                'networks': {
                    'type': 'nested',
                    'properties': {
                        'name': {'type': 'string'},
                        'ipv4': {'type': 'ip'}
                    }
                },
                'fixed_ips': {
                    'type': 'nested',
                    'properties': {
                        'type': {'type': 'string', 'index': 'not_analyzed'},
                        'address': {'type': 'ip'},
                        'version': {'type': 'integer'},
                        'floating_ips': {'type': 'ip'}
                    }
                },
                'image': {
                    'type': 'nested',
                    'properties': {
                        'id': {'type': 'string', 'index': 'not_analyzed'},
                        'container_format': {'type': 'string', 'index': 'not_analyzed'},
                        'min_ram': {'type': 'integer'},
                        'disk_format': {'type': 'string', 'index': 'not_analyzed'},
                        'min_disk': {'type': 'integer'},
                        'kernel_id': {'type': 'string', 'index': 'not_analyzed'},
                        'image_id': {'type': 'string', 'index': 'not_analyzed'} # base_image_ref
                    }
                },
                'state_description': {'type': 'string'},
                'availability_zone': {'type': 'string', 'index': 'not_analyzed'},
                'status': {'type': 'string', 'index': 'not_analyzed'},
                'disk_format': {'type': 'string', 'index': 'not_analyzed'},
                'memory_mb': {'type': 'integer'},
                'vcpus': {'type': 'integer'},
                'disk_gb': {'type': 'integer'},
                'ephemeral_gb': {'type': 'integer'},
            },
        }

    def get_rbac_filter(self, request_context):
        return [
            {
                "and": [
                    {
                        'term': {
                            'owner': request_context.owner
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
        with nc_client.Client(CONF.os_username,
                              CONF.os_password,
                              CONF.os_tenant_name,
                              CONF.os_auth_url) as nc:
            # TODO: paging etc
            return nc.servers.list()

    def serialize(self, server):
        return dict(
            id=server.id,
            instance_id=server.id,
            name=server.name,
            status=server.status.lower(),
            owner=server.tenant_id,
            updated=server.updated,
            created=server.created,
            networks=server.networks,
            availability_zone=getattr(server, 'OS-EXT-AZ:availability_zone', None),
            image=dict(
                # TODO: get the rest
                id=server.image['id']
            ),
            flavor=dict(
                id=server.flavor['id']
            )
        )

    def get_notification_handler(self):
        return instances_notification_handler.InstanceHandler(
            self.engine,
            self.get_index_name(),
            self.get_document_type()
        )

    @staticmethod
    def get_notification_topic_exchange():
        return 'notifications', 'nova'

    def get_notification_supported_events(self):
        # TODO: DRY
        # Most events are duplicated by instance.update
        return [
            'compute.instance.update', 'compute.instance.exists',
            'compute.instance.create.end', 'compute.instance.delete.end',
            'compute.instance.power_on.end', 'compute.instance.power_off.end'
        ]