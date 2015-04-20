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

import copy
import glanceclient.exc
import logging
import six
from oslo_utils import timeutils

from glance.search.plugins import indexing_clients

LOG = logging.getLogger(__name__)


def serialize_glance_image(image):
    g_client = indexing_clients.get_glanceclient()
    if isinstance(image, basestring):
        server = g_client.servers.get(image)

    try:
        members = list(g_client.image_members.list(image.id))
    except glanceclient.exc.HTTPForbidden, e:
        LOG.warning("Could not list image members for %s; forbidden", image.id)
        members = []
        pass

    fields_to_ignore = ['ramdisk_id', 'schema', 'kernel_id', 'file']
    document = dict((k, v) for k, v in image.iteritems()
                    if k not in fields_to_ignore)

    document['members'] = [
        member.member for member in members
        if (member.status == 'accepted' and member.deleted == 0)]

    return document


def serialize_glance_metadef(metadef_ns):
    g_client = indexing_clients.get_glanceclient()
    if isinstance(metadef_ns, basestring):
        metadef_namespace = g_client.metadefs_namespace.get(metadef_ns)

    def serialize_property(prop):
        """
        This is used to serialize both metadef properties AND metadef object
        properties, which follow the same format.
        """
        prop_keys = ['description', 'title', 'type', 'readonly', 'operators']
        doc = dict((k, prop.get(k)) for k in prop_keys)
        # 'name' is not set if this is a metadef object property
        doc['property'] = prop.get('name')
        if 'enum' in prop:
            doc['enum'] = map(str, prop['enum'])
        if 'default' in prop:
            doc['default'] = str(prop['default'])
        return doc

    # Root namespace object
    namespace_fields = ['namespace', 'display_name', 'description',
                        'visibility', 'protected', 'owner']
    document = dict((k, metadef_ns.get(k)) for k in namespace_fields)

    # Namespace properties
    ns_properties = g_client.metadefs_property.list(metadef_ns['namespace'])
    document['properties'] = map(serialize_property, ns_properties)

    # Namespace resource types
    resource_type_fields = ['name', 'prefix', 'properties_target']
    document['resource_types'] = [
        dict((k, rt.get(k)) for k in resource_type_fields)
        for rt in metadef_ns.resource_type_associations

    ]

    # Objects associated with this namespace
    document['objects'] = []
    for ns_object in g_client.metadefs_object.list(metadef_ns['namespace']):
        serialized_obj = {
            'name': ns_object.name,
            'description': ns_object.description,
            'properties': []
        }

        for name, schema in six.iteritems(ns_object.properties):
            obj_prop = serialize_property(schema)
            obj_prop['property'] = name
            serialized_obj['properties'].append(obj_prop)

        document['objects'].append(serialized_obj)

    return document