from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_peeringdb.models.concrete import (
    NetworkIXLan,
)

from fullctl.django.rest.mixins import CachedObjectMixin
from fullctl.django.auth import permissions
from fullctl.django.rest.core import BadRequest
from fullctl.django.rest.decorators import billable, load_object

import django_peerctl.models as models
from django_peerctl.rest.decorators import grainy_endpoint
from django_peerctl.rest.route.peerctl import route
from django_peerctl.rest.serializers.peerctl import Serializers
from django_peerctl.exceptions import UsageLimitError, TemplateRenderError

from django_peerctl.peerses_workflow import (
    PeerSessionEmailWorkflow,
)

from django_peerctl.const import (
    DEVICE_TEMPLATE_TYPES,
    DEVICE_TYPES,
)


@route
class Network(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.net
    queryset = models.Network.objects.all()

    lookup_url_kwarg = "asn"
    lookup_field = "asn"

    # no need to grainy gate this as list filtering does
    # its own permission check

    def list(self, request, *args, **kwargs):
        perms = permissions(request.user)
        perms.load()
        instances = perms.instances(
            models.Network, "crud", explicit=False, ignore_grant_all=True
        )
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)


@route
class Device(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.device
    queryset = models.Device.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.Device.objects.filter(net__asn=asn, status="ok")
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)


@route
class DevicePort(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.port
    queryset = models.Port.objects.all()

    require_asn = True
    require_device = True
    ref_tag = "deviceport"

    @load_object("net", models.Network, asn="asn")
    @load_object("device", models.Device, id="device_pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, net, device_pk, device, *args, **kwargs):
        instances = Port.objects.filter(
            virtport__logport__phyport_qs__in=device.phyport_qs.all(), status="ok"
        )

        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)


# policy view
# list all Polciy for a network
# create
# update
# destroy


@route
class Policy(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.policy
    queryset = models.Policy.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.Policy.objects.filter(net__asn=asn, status="ok")
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        serializer = self.serializer_class(data=request.POST)

        is_global4 = request.POST.get("is_global4", False)
        if is_global4 == "false":
            is_global4 = False

        is_global6 = request.POST.get("is_global6", False)
        if is_global6 == "false":
            is_global6 = False

        b = serializer.is_valid(raise_exception=True)

        policy = serializer.save(net=net, status="ok")

        if is_global4:
            net.policy4 = policy
            net.save()

        if is_global6:
            net.policy6 = policy
            net.save()

        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("policy", models.Policy, id="pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def update(self, request, asn, net, pk, policy, *args, **kwargs):

        serializer = self.serializer_class(instance=policy, data=request.POST)

        is_global4 = request.POST.get("is_global4", False)
        if is_global4 == "false":
            is_global4 = False

        is_global6 = request.POST.get("is_global6", False)
        if is_global6 == "false":
            is_global6 = False

        b = serializer.is_valid(raise_exception=True)

        serializer.save()

        if not is_global4 and net.policy4_id == policy.id:
            net.policy4 = None
            net.save()
        elif is_global4:
            net.policy4 = policy
            net.save()

        if not is_global6 and net.policy6_id == policy.id:
            net.policy6 = None
            net.save()
        elif is_global6:
            net.policy6 = policy
            net.save()

        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("policy", models.Policy, id="pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, pk, policy, *args, **kwargs):
        r = Response(self.serializer_class(policy).data)
        policy.delete()
        return r


@route
class Port(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.port
    queryset = models.Port.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):

        instances = models.Port.objects.filter(portinfo__net__asn=asn, status="ok")
        serializer = self.serializer_class(instances, many=True)

        data = sorted(serializer.data, key=lambda x: x["ix_name"])

        return Response(data)

    @action(detail=True, methods=["get"])
    @load_object("port", models.Port, id="pk", portinfo__net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def devices(self, request, asn, pk, port, *args, **kwargs):
        serializer = Serializers.device(instance=port.devices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["put"])
    @load_object("port", models.Port, id="pk", portinfo__net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_policy(self, request, asn, pk, port, *args, **kwargs):
        ip_version = int(request.POST.get("ipv"))
        policy_id = int(request.POST.get("value"))
        policy = None

        if policy_id:
            policy = models.Policy.objects.get(id=policy_id, net__asn=asn)

        try:
            port.set_policy(policy, ip_version)
        except Exception as exc:
            return BadRequest({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(port)
        return Response(serializer.data)


# peer view
# list all peers for a port and asn
# retrieve peer for port and asn
# details peer details for port and asn


@route
class Peer(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.peer
    queryset = NetworkIXLan.objects.all()
    require_asn = True
    require_port = True

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, net, port_pk, *args, **kwargs):
        port = (
            models.Port.objects.filter(id=port_pk)
            .prefetch_related("peerses_qs")
            .first()
        )
        instances = port.get_available_peers()

        serializer = self.serializer_class(
            instances, many=True, context={"port": port, "net": net}
        )
        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("peer", NetworkIXLan, id="pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def retrieve(self, request, asn, net, port_pk, port, pk, peer, *args, **kwargs):
        serializer = self.serializer_class(peer, context={"port": port, "net": net})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("peer", NetworkIXLan, id="pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def details(self, request, asn, net, port_pk, port, pk, peer, *args, **kwargs):
        serializer = Serializers.peerdetail(peer, context={"port": port, "net": net})
        return Response(serializer.data)

    @action(detail=True, methods=["put"], queryset=NetworkIXLan.objects.all())
    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("netixlan", NetworkIXLan, id="pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_md5(self, request, asn, net, port_pk, port, pk, netixlan, *args, **kwargs):
        peer = models.Network.objects.get(asn=netixlan.net.asn)
        peernet = models.PeerNetwork.get_or_create(net, peer)

        peernet.md5 = request.POST.get("value")
        peernet.save()

        serializer = self.serializer_class(
            instance=netixlan, context={"port": port, "net": net}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["put"], queryset=NetworkIXLan.objects.all())
    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("netixlan", NetworkIXLan, id="pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_max_prefix(
        self, request, asn, net, port_pk, port, pk, netixlan, *args, **kwargs
    ):

        peer = models.Network.objects.get(asn=netixlan.net.asn)
        peernet = models.PeerNetwork.get_or_create(net, peer)

        try:
            peernet.set_info_prefixes(
                request.POST.get("value"), request.POST.get("ipv")
            )
        except ValidationError as exc:
            raise serializers.ValidationError(detail=exc.message_dict)
        except Exception as exc:
            raise serializers.ValidationError({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(
            instance=netixlan, context={"port": port, "net": net}
        )
        return Response(serializer.data)


# peer request view
# create


@route
class PeerRequest(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.peerses
    queryset = models.PeerSession.objects.all()
    require_asn = True
    require_port = True
    require_netixlan = True

    ref_tag = "email_workflow"

    # XXX throttle scopes

    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("netixlan", NetworkIXLan, id="netixlan_pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(
        self, request, asn, net, port_pk, port, netixlan_pk, netixlan, *args, **kwargs
    ):
        workflow = PeerSessionEmailWorkflow(port, netixlan)

        emltmpl_id = int(request.POST.get("emltmpl", 0))
        content = request.POST.get("body")

        if emltmpl_id > 0:
            emltmpl = models.EmailTemplate.objects.get(id=emltmpl_id)
        else:
            emltmpl = models.EmailTemplate(type=workflow.next_step, net=net)

        # if content is passed with request, override it
        if content:
            emltmpl.content_override = content

        try:
            peerses = workflow.progress(request.user, emltmpl)
        except TemplateRenderError as exc:
            raise serializers.ValidationError({"non_field_errors": ["{}".format(exc)]})
        except UsageLimitError as exc:
            raise serializers.ValidationError(
                {"non_field_errors": [["usage_limit", "{}".format(exc)]]}
            )

        serializer = Serializers.peer(
            [ps.peerport.portinfo.pdb for ps in peerses],
            many=True,
            context={"port": port, "net": net},
        )
        return Response(serializer.data)


# peer session view
# create


@route
class PeerSession(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.peerses
    queryset = models.PeerSession.objects.all()
    require_asn = True
    require_port = True

    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, port_pk, port, *args, **kwargs):
        data = request.POST.dict()

        netixlan = NetworkIXLan.objects.get(id=data.get("netixlan"))

        if data.get("through"):
            through_netixlan = NetworkIXLan.objects.get(id=data.get("through"))
        else:
            through_netixlan = netixlan

        peerport = models.PeerPort.get_or_create_from_netixlans(
            models.Port.objects.get(id=port_pk).portinfo.pdb, netixlan
        )

        # XXX aaactl metered limiting
        # try:
        #    port.portinfo.net.validate_limits()
        # except UsageLimitError as exc:
        #    raise serializers.ValidationError(
        #        {"non_field_errors": [["usage_limit", "{}".format(exc)]]}
        #    )

        instance = models.PeerSession.get_or_create(port, peerport)
        instance.status = "ok"
        instance.save()

        models.AuditLog.log_peerses_add(instance, request.user)

        serializer = Serializers.peer(
            through_netixlan, context={"port": port, "net": net}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["put"])
    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("peerses", models.PeerSession, id="pk", port__portinfo__net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def set_policy(
        self, request, asn, net, port_pk, port, pk, peerses, *args, **kwargs
    ):
        ip_version = int(request.POST.get("ipv"))
        policy_id = int(request.POST.get("value"))
        policy = None

        if policy_id:
            policy = models.Policy.objects.get(id=policy_id, net__asn=asn)

        try:
            peerses.set_policy(policy, ip_version)
        except Exception as exc:
            return BadRequest({"non_field_errors": [[str(exc)]]})

        serializer = self.serializer_class(peerses)
        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("port", models.Port, id="port_pk")
    @load_object("peerses", models.PeerSession, id="pk", port__portinfo__net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, port_pk, port, pk, peerses, *args, **kwargs):
        r = super().destroy(request, asn, port, pk)
        # XXX: fullctl auditlog covers this
        models.AuditLog.log_peerses_del(peerses, request.user)
        return Response(self.serializer_class(peerses).data)


@route
class UserPreferences(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.userpref
    queryset = models.UserPreferences.objects.all()

    def update(self, request, pk=None, *args, **kwargs):
        userpref = models.UserPreferences.get_or_create(request.user)
        serializer = self.serializer_class(userpref, data=request.POST)
        b = serializer.is_valid(raise_exception=True)
        serializer.save(user_id=request.user.id, status="ok")
        return Response(serializer.data)

    def list(self, request):
        userpref = models.UserPreferences.get_or_create(request.user)
        serializer = self.serializer_class(instance=userpref)
        return Response(serializer.data)


# email template
# list
# create
# preview


@route
class EmailTemplate(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.emltmpl
    queryset = models.EmailTemplate.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.EmailTemplate.objects.filter(status="ok", net__asn=asn)
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("tmpl", models.EmailTemplate, id="pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, pk, tmpl, *args, **kwargs):
        r = Response(self.serializer_class(tmpl).data)
        tmpl.delete()
        return r

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        serializer = self.serializer_class(data=request.POST)
        b = serializer.is_valid(raise_exception=True)
        serializer.save(net_id=net.id, status="ok")
        return Response(serializer.data)

    @action(detail=False, methods=["post", "get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def preview_blank(self, request, asn, net, *args, **kwargs):
        return self._preview(request, asn, net, "0", *args, **kwargs)

    @action(detail=True, methods=["post", "get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def preview(self, request, asn, net, pk, *args, **kwargs):
        return self._preview(request, asn, net, pk, *args, **kwargs)

    def _preview(self, request, asn, net, pk, *args, **kwargs):
        """
        Template preview

        expects `body` and `type` in POST

        Renders TemplatePreviewSerializer response
        """
        if not pk or pk == "0":
            emltmpl = models.EmailTemplate(
                name="Preview",
                net=net,
                body=request.POST.get("body"),
                type=request.POST.get("type"),
            )
        else:
            emltmpl = models.EmailTemplate.objects.get(id=pk)

        if "peer" in request.POST:
            emltmpl.context["peer"] = NetworkIXLan.objects.get(id=request.POST["peer"])
        else:
            emltmpl.context["peer"] = NetworkIXLan.objects.filter(
                asn=asn, status="ok"
            ).first()

        if "peerses" in request.POST:
            emltmpl.context["sessions"] = models.PeerSession.objects.filter(
                id=request.POST["peerses"]
            )

        serializer = Serializers.tmplpreview(instance=emltmpl)
        return Response(serializer.data)


# device template
# list
# create
# preview


@route
class DeviceTemplate(CachedObjectMixin, viewsets.ModelViewSet):

    serializer_class = Serializers.devicetmpl
    queryset = models.DeviceTemplate.objects.all()
    require_asn = True

    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list(self, request, asn, *args, **kwargs):
        instances = models.DeviceTemplate.objects.filter(status="ok", net__asn=asn)
        serializer = self.serializer_class(instances, many=True)
        return Response(serializer.data)

    @load_object("net", models.Network, asn="asn")
    @load_object("tmpl", models.DeviceTemplate, id="pk", net__asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def destroy(self, request, asn, net, pk, tmpl, *args, **kwargs):
        r = Response(self.serializer_class(tmpl).data)
        tmpl.delete()
        return r

    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def create(self, request, asn, net, *args, **kwargs):
        serializer = self.serializer_class(data=request.POST)
        b = serializer.is_valid(raise_exception=True)
        serializer.save(net_id=net.id, status="ok")
        return Response(serializer.data)

    @action(detail=False, methods=["post", "get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def preview_blank(self, request, asn, net, *args, **kwargs):
        return self._preview(request, asn, net, "0", *args, **kwargs)

    @action(detail=True, methods=["post", "get"])
    @load_object("net", models.Network, asn="asn")
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def preview(self, request, asn, net, pk, *args, **kwargs):
        return self._preview(request, asn, net, pk, *args, **kwargs)

    def _preview(self, request, asn, net, pk, *args, **kwargs):
        print("got here")
        if not pk or pk == "0":
            devicetmpl = models.DeviceTemplate(
                name="Preview",
                net=net,
                body=request.POST.get("body"),
                type=request.POST.get("type"),
            )
        else:
            devicetmpl = models.DeviceTemplate.objects.get(id=pk)

        port = net.portinfo_qs.first().port_qs.first()
        devicetmpl.context["port"] = port
        devicetmpl.context["net"] = net
        # FIXME: support more than one physical port in templates (expose multiple devices?)
        devicetmpl.context["device"] = models.Device.objects.get(
            net=net, pk=request.POST.get("device")
        )

        devicetmpl.context["netixlan"] = request.POST.get("netixlan")

        serializer = Serializers.tmplpreview(instance=devicetmpl)
        return Response(serializer.data)

    @action(detail=False)
    @grainy_endpoint(namespace="verified.asn.{asn}.?")
    def list_available(self, request, asn, *args, **kwargs):
        # load default templates (netom)
        data = [{"id": tmpl[0], "name": tmpl[1]} for tmpl in DEVICE_TEMPLATE_TYPES]

        # if a device type is specified in url parameters we
        # only want to display template types for this device type
        devtyp = request.GET.get("device_type")
        devtypes = dict(DEVICE_TYPES)
        if devtyp:
            devname = devtypes.get(devtyp)
            trimmed = []
            for tmpl in data:
                if tmpl["id"].find(f"{devtyp}-") == 0:
                    # remove device type label from template label
                    # as it's redundant when specifying a device
                    tmpl["name"] = tmpl["name"].replace(devname + " ", "")
                    trimmed.append(tmpl)
            data = trimmed

        serializer = Serializers.devicelist(data, many=True)
        return Response(serializer.data)


# bulk email
