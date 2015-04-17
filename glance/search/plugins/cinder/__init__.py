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

from glance.search.plugins import indexing_clients


def serialize_volume(volume):
    if isinstance(volume, basestring):
        volume = indexing_clients.get_cinderclient().volumes.get(volume)

    return dict(
        id=volume.id,
        availability_zone=volume.availability_zone,
        created_at=volume.created_at,
        name=volume.name,
        owner=getattr(volume, 'os-vol-tenant-attr:tenant_id'),
        tenant_id=getattr(volume, 'os-vol-tenant-attr:tenant_id'),
        encrypted=volume.encrypted,
        description=volume.description,
        volume_type=volume.volume_type,
        status=volume.status,
        user_id=volume.user_id,
        bootable=volume.bootable,
        attachments=volume.attachments
    )
