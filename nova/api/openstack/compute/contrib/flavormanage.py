# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License

import webob

from nova.api.openstack.compute import flavors as flavors_api
from nova.api.openstack.compute.views import flavors as flavors_view
from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.compute import instance_types
from nova import exception


authorize = extensions.extension_authorizer('compute', 'flavormanage')


class FlavorManageController(wsgi.Controller):
    """
    The Flavor Lifecycle API controller for the OpenStack API.
    """
    _view_builder_class = flavors_view.ViewBuilder

    def __init__(self):
        super(FlavorManageController, self).__init__()

    @wsgi.action("delete")
    def _delete(self, req, id):
        context = req.environ['nova.context']
        authorize(context)

        try:
            flavor = instance_types.get_instance_type_by_flavor_id(
                    id, read_deleted="no")
        except exception.NotFound, e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())

        instance_types.destroy(flavor['name'])

        return webob.Response(status_int=202)

    @wsgi.action("create")
    @wsgi.serializers(xml=flavors_api.FlavorTemplate)
    def _create(self, req, body):
        context = req.environ['nova.context']
        authorize(context)

        vals = body['flavor']
        name = vals['name']
        flavorid = vals.get('id')
        memory_mb = vals.get('ram')
        vcpus = vals.get('vcpus')
        root_gb = vals.get('disk')
        ephemeral_gb = vals.get('OS-FLV-EXT-DATA:ephemeral')
        swap = vals.get('swap')
        rxtx_factor = vals.get('rxtx_factor')
        is_public = vals.get('os-flavor-access:is_public', True)

        try:
            flavor = instance_types.create(name, memory_mb, vcpus,
                                           root_gb, ephemeral_gb, flavorid,
                                           swap, rxtx_factor, is_public)
            req.cache_db_flavor(flavor)
        except (exception.InstanceTypeExists,
                exception.InstanceTypeIdExists) as err:
            raise webob.exc.HTTPConflict(explanation=err.format_message())

        return self._view_builder.show(req, flavor)


class Flavormanage(extensions.ExtensionDescriptor):
    """
    Flavor create/delete API support
    """

    name = "FlavorManage"
    alias = "os-flavor-manage"
    namespace = ("http://docs.openstack.org/compute/ext/"
                 "flavor_manage/api/v1.1")
    updated = "2012-01-19T00:00:00+00:00"

    def get_controller_extensions(self):
        controller = FlavorManageController()
        extension = extensions.ControllerExtension(self, 'flavors', controller)
        return [extension]
