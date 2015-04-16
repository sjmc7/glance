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

import functools
from keystoneclient.v2_0 import client as ksclient
from novaclient import client as nclient
from glanceclient import client as gclient
from oslo_config import cfg
import os

CLI_OPTS = [
    cfg.StrOpt('os-username',
               deprecated_group="DEFAULT",
               default=os.environ.get('OS_USERNAME', 'glance'),
               help='User name to use for OpenStack service access.'),
    cfg.StrOpt('os-password',
               deprecated_group="DEFAULT",
               secret=True,
               default=os.environ.get('OS_PASSWORD', 'admin'),
               help='Password to use for OpenStack service access.'),
    cfg.StrOpt('os-tenant-id',
               deprecated_group="DEFAULT",
               default=os.environ.get('OS_TENANT_ID', ''),
               help='Tenant ID to use for OpenStack service access.'),
    cfg.StrOpt('os-tenant-name',
               deprecated_group="DEFAULT",
               default=os.environ.get('OS_TENANT_NAME', 'admin'),
               help='Tenant name to use for OpenStack service access.'),
    cfg.StrOpt('os-cacert',
               default=os.environ.get('OS_CACERT'),
               help='Certificate chain for SSL validation.'),
    cfg.StrOpt('os-auth-url',
               deprecated_group="DEFAULT",
               default=os.environ.get('OS_AUTH_URL',
                                      'http://localhost:5000/v2.0'),
               help='Auth URL to use for OpenStack service access.'),
    cfg.StrOpt('os-region-name',
               deprecated_group="DEFAULT",
               default=os.environ.get('OS_REGION_NAME'),
               help='Region name to use for OpenStack service endpoints.'),
    cfg.StrOpt('os-endpoint-type',
               default=os.environ.get('OS_ENDPOINT_TYPE', 'publicURL'),
               help='Type of endpoint in Identity service catalog to use for '
                    'communication with OpenStack services.'),
    cfg.BoolOpt('insecure',
                default=False,
                help='Disables X.509 certificate validation when an '
                     'SSL connection to Identity Service is established.'),
]
cfg.CONF.register_cli_opts(CLI_OPTS, group="service_credentials")


def memoized(fn):
    """A poor-mans memoizer. Doesn't care what arguments are given. Stores
    the function result in fn.cached.
    """
    def wrapper(*args, **kwargs):
        cached = getattr(fn, 'cached', None)
        if not cached:
            setattr(fn, 'cached', fn(*args, **kwargs))
        return fn.cached
    return wrapper

@memoized
def get_keystoneclient():
    return ksclient.Client(
        username=cfg.CONF.service_credentials.os_username,
        password=cfg.CONF.service_credentials.os_password,
        tenant_id=cfg.CONF.service_credentials.os_tenant_id,
        tenant_name=cfg.CONF.service_credentials.os_tenant_name,
        cacert=cfg.CONF.service_credentials.os_cacert,
        auth_url=cfg.CONF.service_credentials.os_auth_url,
        region_name=cfg.CONF.service_credentials.os_region_name,
        insecure=cfg.CONF.service_credentials.insecure)

@memoized
def get_novaclient():
    ks_client = get_keystoneclient()
    endpoint = ks_client.service_catalog.url_for(
        service_type='compute')

    return nclient.Client(
        version=2,
        endpoint=endpoint,
        auth_token=ks_client.auth_token,
        auth_url=ks_client.auth_url,
        tenant_name=ks_client.tenant_name,
        tenant_id=ks_client.tenant_id,
        username=ks_client.username
    )

@memoized
def get_glanceclient():
    ks_client = get_keystoneclient()
    endpoint = ks_client.service_catalog.url_for(
        service_type='image')

    return gclient.Client(
        version=2,
        endpoint=endpoint,
        token=ks_client.auth_token,
        auth_url=ks_client.auth_url,
        tenant_name=ks_client.tenant_name,
        tenant_id=ks_client.tenant_id,
        username=ks_client.username
    )
