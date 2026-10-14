"""Composition function for the GCP Network.

Adapts core.py to Crossplane's gRPC API: reads the XR, composes, and publishes the status other
domains consume.
"""

import grpc
from crossplane.function import logging, resource, response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1
from models.io.upbound.platform.gcp.network import v1alpha1 as platformv1alpha1
from pydantic import ValidationError

from . import core
from .serialize import to_dict


class FunctionRunner(grpcv1.FunctionRunnerService):
    """A FunctionRunner handles gRPC RunFunctionRequests."""

    def __init__(self):
        """Create a new FunctionRunner."""
        self.log = logging.get_logger()

    async def RunFunction(
        self, req: fnv1.RunFunctionRequest, _: grpc.aio.ServicerContext
    ) -> fnv1.RunFunctionResponse:
        """Run the function."""
        log = self.log.bind(tag=req.meta.tag)
        rsp = response.to(req)

        xr = resource.struct_to_dict(req.observed.composite.resource)
        # The API server enforces the XRD schema, but offline renders and composition tests
        # don't, so check the XR against the model generated from it.
        try:
            platformv1alpha1.Network(**xr)
        except ValidationError as e:
            response.fatal(rsp, f"invalid Network: {e}")
            return rsp

        meta = xr["metadata"]
        params = xr["spec"]["parameters"]
        errors = core.validate(params)
        if errors:
            response.fatal(rsp, "; ".join(errors))
            return rsp

        observed = {
            name: resource.struct_to_dict(r.resource) for name, r in req.observed.resources.items()
        }
        desired = core.build(meta.get("name"), meta.get("namespace"), params, observed=observed)
        for name, model in desired.items():
            resource.update(rsp.desired.resources[name], to_dict(model))

        status = core.status(params, observed)
        resource.update(rsp.desired.composite, {"status": status})

        log.info(
            "Composed network",
            resources=len(desired),
            vpc=status["vpc"].get("selfLink", "<pending>"),
            subnetwork=status["subnetwork"].get("selfLink", "<pending>"),
        )
        return rsp
