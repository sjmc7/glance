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

from glance.search.plugins import indexing_clients

def serialize_nova_server(server):
    nc_client = indexing_clients.get_novaclient()
    if isinstance(server, basestring):
        server = nc_client.servers.get(server)

    glance_image = indexing_clients.get_glanceclient().images.get(server.image['id'])

    flavor = nc_client.flavors.get(server.flavor['id'])

    serialized = dict(
        id=server.id,
        instance_id=server.id,
        name=server.name,
        status=server.status.lower(),
        owner=server.tenant_id,
        updated=server.updated,
        created=server.created,
        networks=server.networks,
        availability_zone=getattr(server, 'OS-EXT-AZ:availability_zone', None),
        key_name=server.key_name,
        image=dict(
            # TODO: get the rest
            id=server.image['id'],
            name=glance_image['name'],
        ),
        flavor=dict(
            id=server.flavor['id'],
            name=flavor.name,
            ram=flavor.ram,
            disk=flavor.disk,
            ephemeral=flavor.ephemeral,
            vcpus=flavor.vcpus
        ),
        fixed_ips=[],
    )
    serialized['OS-EXT-STS:power_state'] = getattr(server, 'OS-EXT-STS:power_state')
    serialized['OS-EXT-STS:task_state'] = getattr(server, 'OS-EXT-STS:task_state')
    return serialized