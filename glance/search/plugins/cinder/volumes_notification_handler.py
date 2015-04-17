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

from oslo_log import log as logging
import oslo_messaging

from glance.search.plugins import base
from glance.common import utils
import novaclient.exceptions

from . import serialize_volume


LOG = logging.getLogger(__name__)


class VolumeHandler(base.NotificationBase):
    """Handles nova server notifications. These can come as a result of
    a user action (like a name change, state change etc) or as a result of
    periodic auditing notifications nova sends
    """
    def __init__(self, *args, **kwargs):
        super(VolumeHandler, self).__init__(*args, **kwargs)

    def process(self, ctxt, publisher_id, event_type, payload, metadata):
        LOG.debug("Received cinder event %s for instance %s",
                  event_type,
                  payload.get('volume_id', '<unknown>'))
        try:
            actions = {
                'volume.create.end': self.create_or_update,
                'volume.update.end': self.create_or_update,
                'volume.delete.end': self.delete
            }
            actions[event_type](payload)
            return oslo_messaging.NotificationResult.HANDLED
        except Exception as e:
            LOG.error(utils.exception_to_str(e))

    def create_or_update(self, payload):
        volume_id = payload['volume_id']
        LOG.debug("Updating cinder volume information for %s", volume_id)
        if not volume_id:
            return

        payload = serialize_volume(volume_id)

        body = {
            'doc': payload,
            'doc_as_upsert': True,
        },
        self.engine.update(
            index=self.index_name,
            doc_type=self.document_type,
            body=body,
            id=volume_id
        )

    def delete(self, payload):
        volume_id = payload['volume_id']
        LOG.debug("Deleting cinder volume information for %s", volume_id)
        if not volume_id:
            return

        self.engine.delete(
            index=self.index_name,
            doc_type=self.document_type,
            id=volume_id
        )