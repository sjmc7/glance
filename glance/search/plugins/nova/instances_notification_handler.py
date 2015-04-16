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

import datetime
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging

from glance.search.plugins import base
from glance.search.plugins import indexing_clients
from glance.common import utils
from novaclient.v2 import client as nc_client
import novaclient.exceptions

from . import serialize_nova_server

LOG = logging.getLogger(__name__)


class InstanceHandler(base.NotificationBase):
    """Handles nova server notifications. These can come as a result of
    a user action (like a name change, state change etc) or as a result of
    periodic auditing notifications nova sends
    """
    def __init__(self, *args, **kwargs):
        super(InstanceHandler, self).__init__(*args, **kwargs)
        self.image_delete_keys = ['deleted_at', 'deleted',
                                  'is_public', 'properties']
        self._ks_client = None
        self._n_client = None

    @property
    def keystoneclient(self):
        if self._ks_client is None:
            self._ks_client = indexing_clients.get_keystoneclient()
        return self._ks_client

    @property
    def novaclient(self):
        if self._n_client is None:
            self._n_client = indexing_clients.get_novaclient(self.keystoneclient)
        return self._n_client

    def process(self, ctxt, publisher_id, event_type, payload, metadata):
        LOG.debug("Received nova event %s for instance %s",
                  event_type,
                  payload.get('instance_id', '<unknown>'))
        try:
            actions = {
                # compute.instance.update seems to be the event set as a
                # result of a state change etc
                'compute.instance.update': self.create_or_update,
                'compute.instance.exists': self.create_or_update,
                'compute.instance.create.end': self.create_or_update,
                'compute.instance.power_on.end': self.create_or_update,
                'compute.instance.power_off.end': self.create_or_update,
                'compute.instance.delete.end': self.delete,

                # Neutron events
                'port.create.end': self.update_neutron_ports,
                #'port.delete.end': self.update_neutron_ports,
            }
            actions[event_type](payload)
            return oslo_messaging.NotificationResult.HANDLED
        except Exception as e:
            LOG.error(utils.exception_to_str(e))

    def create_or_update(self, payload):
        instance_id = payload['instance_id']
        LOG.debug("Updating nova instance information for %s", instance_id)

        try:
            payload = serialize_nova_server(self.novaclient, None, instance_id)
        except novaclient.exceptions.NotFound, e:
            # Todo: delete? probably
            LOG.warning("Instance id %s not found", instance_id)
            return

        #payload = self.format_server(payload)

        body = {
            'doc': payload,
            'doc_as_upsert': True,
        },
        self.engine.update(
            index=self.index_name,
            doc_type=self.document_type,
            body=body,
            id=instance_id
        )

    def delete(self, payload):
        instance_id = payload['instance_id']
        LOG.debug("Deleting nova instance information for %s", instance_id)
        if not instance_id:
            return

        self.engine.delete(
            index=self.index_name,
            doc_type=self.document_type,
            id=instance_id
        )

    def update_neutron_ports(self, payload):
        instance_id = payload['port']['device_id']
        LOG.debug("Updating neutron port information for instance %s", instance_id)
        if not instance_id:
            return

        LOG.warning("%s", payload)

        doc = {
            'doc': {
                'id': instance_id,
                'instance_id': instance_id,
                'fixed_ips': [
                    {
                        'address': fip['ip_address'],
                        'type': 'fixed',
                    } for fip in payload['port']['fixed_ips']
                ]
            },
            'doc_as_upsert': True
        }
        self.engine.update(
            index=self.index_name,
            doc_type=self.document_type,
            body=doc,
            id=instance_id
        )

    def format_server(self, payload):
        # TODO: Maybe the index should be more similar to the notification
        # structure? Notifications have a LOT more information than do
        # what we can get from a single nova call, though missing some stuff,
        # notably networking info
        #
        # https://wiki.openstack.org/wiki/SystemUsageData

        # Common attributes
        formatted = dict(
            id=payload['instance_id'],
            instance_id=payload['instance_id'],
            name=payload['display_name'],
            status=payload['state'],
            state_description=payload['state_description'],
            owner=payload['tenant_id'],
            updated=datetime.datetime.utcnow(), # TODO: Not this.
            created=payload['created_at'].replace(' ', 'T'),
            # networks=server.networks,  # TODO: Figure this out
            availability_zone=payload.get('availability_zone', None),
            vcpus=payload['vcpus'],
            disk_gb=payload['disk_gb'],
            memory_mb=payload['memory_mb'],
            ephemeral_gb=payload['ephemeral_gb'],
            image=dict(
                id=payload['image_meta']['base_image_ref'],
                kernel_id=payload['image_meta']['kernel_id'],
                #name=bizarrely not here
                container_format=payload['image_meta']['container_format'],
                disk_format=payload['image_meta']['disk_format'],
                min_disk=payload['image_meta']['min_disk'],
                min_ram=payload['image_meta']['min_ram'],
            ),
            flavor=dict(
                id=payload['instance_flavor_id'],
                name=payload['instance_type'],
            )
        )
        if 'fixed_ips' in payload:
            fixed_ips = [
                {'address': fip['address'],
                 'type': fip['type']
                } for fip in payload['fixed_ips']
            ]

        return formatted
