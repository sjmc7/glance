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


INDEX_FLAVORS = True
INDEX_IMAGES = True


@indexing_clients.clear_cache_on_unauthorized
def serialize_nova_server(server):
    nc_client = indexing_clients.get_novaclient()
    if isinstance(server, basestring):
        server = nc_client.servers.get(server)

    if INDEX_FLAVORS:
        flavor = nc_client.flavors.get(server.flavor['id'])
    if INDEX_IMAGES:
        image = indexing_clients.get_glanceclient().images.get(server.image['id'])

    serialized = dict(
        id=server.id,
        instance_id=server.id,
        name=server.name,
        status=server.status.lower(),
        owner=server.tenant_id,
        tenant_id=server.tenant_id,
        user_id=server.user_id,
        updated=server.updated,
        created=server.created,
        metadata=server.metadata,
        networks=server.networks,
        availability_zone=getattr(server, 'OS-EXT-AZ:availability_zone', None),
        host=getattr(server, 'OS-EXT-SRV-ATTR:host', None),
        key_name=server.key_name,
        image={'id': server.image['id']},
        flavor={
            'id': server.flavor['id']
        }
    )
    # TODO: turn these into useful strings?
    serialized['OS-EXT-STS:power_state'] = getattr(server, 'OS-EXT-STS:power_state')
    serialized['OS-EXT-STS:task_state'] = getattr(server, 'OS-EXT-STS:task_state')

    if INDEX_FLAVORS:
        serialized['flavor']['name'] = flavor.name
        serialized['flavor']['ram'] = flavor.ram
        serialized['flavor']['ephemeral'] = flavor.ephemeral
        serialized['flavor']['vcpus'] = flavor.vcpus
        serialized['flavor']['disk'] = flavor.disk

    if INDEX_IMAGES:
        serialized['image']['name'] = image.name


    return serialized