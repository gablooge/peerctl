from fullctl.django.models.concrete import Task
from fullctl.django.tasks import register

from django_peerctl.autopeer.workflow import AutopeerWorkflow

import json

__all__ = [
    "AutopeerRequest",
]

@register
class AutopeerRequest(Task):

    """
    Autopeer request from one network to another

    Expected arguments during create task:

    - asn (int)
    - to_asn (int)
    """

    class Meta:
        proxy = True

    class TaskMeta:
        limit = 1

    class HandleRef:
        tag = "task_autopeer_request"

    @property
    def generate_limit_id(self):
        # as a task limiter we use the two asns delimited by a dash
        return str(self.asn)+"-"+str(self.to_asn)

    @property
    def asn(self):
        return self.param["args"][0]

    @property
    def to_asn(self):
        return self.param["args"][1]

    def run(self, from_asn, to_asn, *args, **kwargs):
        workflow = AutopeerWorkflow(from_asn, to_asn)
        return json.dumps(workflow.request())

