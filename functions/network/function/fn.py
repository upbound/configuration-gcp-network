"""Composition function for the GCP Network.

A Network composes a custom-mode VPC network and one regional subnetwork with secondary ranges for
GKE pods and services. Both are named from spec.parameters.id, and either can adopt an existing GCP
object through spec.parameters.externalNames.
"""

import re

import grpc
from crossplane.function import logging, resource, response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1
from models.io.k8s.apimachinery.pkg.apis.meta import v1 as metav1
from models.io.upbound.m.gcp.compute.network import v1beta1 as networkv1beta1
from models.io.upbound.m.gcp.compute.subnetwork import v1beta1 as subnetworkv1beta1
from models.io.upbound.platform.gcp.network import v1alpha1 as platformv1alpha1
from pydantic import BaseModel, ValidationError

# Composition resource names identify composed resources across reconciles, and are the keys of
# spec.parameters.externalNames. Never rename them.
NETWORK = "network"
SUBNETWORK = "subnetwork"
EXTERNAL_NAME_KEYS = [NETWORK, SUBNETWORK]

NETWORK_ID_LABEL = "networks.gcp.platform.upbound.io/network-id"
EXTERNAL_NAME_ANNOTATION = "crossplane.io/external-name"

# GCP's rule for network and subnetwork names, which it enforces only at apply.
# https://cloud.google.com/compute/docs/reference/rest/v1/subnetworks/insert
NAME_PATTERN = re.compile(r"[a-z]([-a-z0-9]*[a-z0-9])?")
NAME_MAX_LENGTH = 63


def _valid_name(name: str) -> bool:
    return len(name) <= NAME_MAX_LENGTH and NAME_PATTERN.fullmatch(name) is not None


def _list(items: list[str]) -> str:
    """Format a list as [a, b], the form these error messages have always used."""
    return f"[{', '.join(items)}]"


def compose(xr: platformv1alpha1.Network) -> dict[str, BaseModel]:
    """Return the desired composed resources, keyed by composition resource name.

    Raises ValueError when the parameters would compose resources GCP rejects or that adopt
    nothing. The XRD already rejects empty externalNames values.
    """
    params = xr.spec.parameters
    external_names = params.externalNames or {}

    # An unknown key would create a duplicate instead of adopting.
    unknown = [k for k in external_names if k not in EXTERNAL_NAME_KEYS]
    if unknown:
        raise ValueError(
            f"spec.parameters.externalNames has unknown key(s) {_list(unknown)}; "
            f"valid keys for this Network are {_list(EXTERNAL_NAME_KEYS)}"
        )

    network_name = external_names.get(NETWORK, params.id)
    if not _valid_name(network_name):
        raise ValueError(
            f"spec.parameters.id yields network name '{network_name}', which is not a valid "
            "compute network name; a name is at most 63 characters, lowercase letters, numbers "
            "and hyphens, starts with a letter and ends with a letter or number, so adjust "
            "spec.parameters.id"
        )

    # A subnetwork is name-as-identifier, so metadata.name is its GCP name unless it's adopted.
    subnetwork_name = f"{params.id}-subnetwork"
    if SUBNETWORK not in external_names and not _valid_name(subnetwork_name):
        raise ValueError(
            f"spec.parameters.id yields derived name(s) ['{subnetwork_name}'], which are not "
            "valid subnetwork names; the subnetwork is named '{id}-subnetwork' and a name is at "
            "most 63 characters, lowercase letters, numbers and hyphens, starting with a letter "
            "and ending with a letter or number, so keep spec.parameters.id at 52 characters or "
            "fewer"
        )

    def metadata(name: str, resource_name: str) -> metav1.ObjectMeta:
        annotations = None
        if resource_name in external_names:
            annotations = {EXTERNAL_NAME_ANNOTATION: external_names[resource_name]}
        return metav1.ObjectMeta(
            name=name,
            annotations=annotations,
            labels={NETWORK_ID_LABEL: params.id},
        )

    policies = params.managementPolicies or ["*"]
    # Without a ProviderConfig name, leave providerConfigRef to the API server's default.
    provider_config_ref = None
    if params.providerConfigName:
        provider_config_ref = {"kind": "ProviderConfig", "name": params.providerConfigName}

    return {
        NETWORK: networkv1beta1.Network(
            metadata=metadata(params.id, NETWORK),
            spec=networkv1beta1.Spec(
                managementPolicies=policies,
                providerConfigRef=provider_config_ref,
                forProvider=networkv1beta1.ForProvider(
                    autoCreateSubnetworks=False,
                    routingMode="REGIONAL",
                ),
            ),
        ),
        SUBNETWORK: subnetworkv1beta1.Subnetwork(
            metadata=metadata(subnetwork_name, SUBNETWORK),
            spec=subnetworkv1beta1.Spec(
                managementPolicies=policies,
                providerConfigRef=provider_config_ref,
                forProvider=subnetworkv1beta1.ForProvider(
                    ipCidrRange="172.16.0.0/16",
                    region=params.region,
                    networkSelector=subnetworkv1beta1.NetworkSelector(matchControllerRef=True),
                    privateIpGoogleAccess=True,
                    secondaryIpRange=[
                        subnetworkv1beta1.SecondaryIpRangeItem(
                            ipCidrRange="10.200.0.0/14", rangeName="pods"
                        ),
                        subnetworkv1beta1.SecondaryIpRangeItem(
                            ipCidrRange="10.204.0.0/16", rangeName="services"
                        ),
                    ],
                ),
            ),
        ),
    }


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

        try:
            xr = platformv1alpha1.Network(
                **resource.struct_to_dict(req.observed.composite.resource)
            )
        except ValidationError as e:
            response.fatal(rsp, f"invalid Network: {e}")
            return rsp

        try:
            desired = compose(xr)
        except ValueError as e:
            response.fatal(rsp, str(e))
            return rsp

        # Dump rather than pass the models so that schema defaults, such as
        # managementPolicies, are emitted.
        for name, r in desired.items():
            resource.update(
                rsp.desired.resources[name], r.model_dump(exclude_none=True, by_alias=True)
            )

        log.info("Composed resources", count=len(desired))
        return rsp
