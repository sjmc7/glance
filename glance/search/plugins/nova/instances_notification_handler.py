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
from glance.common import utils
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
            payload = serialize_nova_server(instance_id)
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
