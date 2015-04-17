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

from glanceclient import client as gc_client
from oslo_config import cfg

from glance.search.plugins import indexing_clients
from glance.search.plugins import base

from . import serialize_volume
from . import volumes_notification_handler



class VolumeIndex(base.IndexBase):
    def __init__(self):
        super(VolumeIndex, self).__init__()

    def get_index_name(self):
        return "cinder"

    def get_document_type(self):
        return "volume"

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

    def get_mapping(self):
        str_n_a = {'type': 'string', 'index': 'not_analyzed'}
        return {
            'dynamic': True,
            'properties': {
                'id': str_n_a,
                'name': {'type': 'string'},
                'size': {'type': 'integer'},
                'owner': str_n_a,
                'tenant_id': str_n_a,
                'user_id': str_n_a,
                'status':  str_n_a,
                'availability_zone': str_n_a,
                'created_at': {'type': 'date'},
                'volume_type': str_n_a,
                'description': {'type': 'string'},
                'encrypted': {'type': 'boolean'},
                'bootable': {'type': 'boolean'},
                'attachments': str_n_a,  # Represent as a list of server ids
            }
        }

    def get_notification_handler(self):
        return volumes_notification_handler.VolumeHandler(
            self.engine,
            self.get_index_name(),
            self.get_document_type()
        )

    def get_objects(self):
        return indexing_clients.get_cinderclient().volumes.list()

    @staticmethod
    def get_notification_topic_exchanges():
        return (
            ('notifications', 'cinder'),
        )

    def get_notification_supported_events(self):
        # TODO: DRY
        # Most events are duplicated by instance.update
        return [
            'volume.create.end', 'volume.delete.end', 'volume.update.end'
        ]

    def serialize(self, obj):
        return serialize_volume(obj)
