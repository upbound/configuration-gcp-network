"""Build the composed resources and the published status for one Network XR.

A Network composes a custom-mode VPC network and one regional subnetwork with secondary ranges for
GKE pods and services. Both are named from spec.parameters.id, and either can adopt an existing GCP
object through spec.parameters.externalNames.

Resources are built from the models `up` generates from the provider's CRDs, so field names and
nesting are checked at construction rather than rejected later by the API server. Nothing here
talks to Crossplane: fn.py does that, which keeps this module directly testable.
"""

import re

from models.io.k8s.apimachinery.pkg.apis.meta import v1 as metav1
from models.io.upbound.m.gcp.compute.network import v1beta1 as networkv1beta1
from models.io.upbound.m.gcp.compute.subnetwork import v1beta1 as subnetworkv1beta1
from pydantic import BaseModel

# Composition resource names identify composed resources across reconciles, and are the keys of
# spec.parameters.externalNames. Never rename them.
NETWORK = "network"
SUBNETWORK = "subnetwork"
EXTERNAL_NAME_KEYS = [NETWORK, SUBNETWORK]

# GKE and SQLInstance XRs that predate status.vpc select these resources by this label, so it
# stays even though consumers should now read the published status instead.
NETWORK_ID_LABEL = "networks.gcp.platform.upbound.io/network-id"
EXTERNAL_NAME_ANNOTATION = "crossplane.io/external-name"

SUBNETWORK_CIDR = "172.16.0.0/16"
# Range names are published in status for GKE's IP allocation policy; the CIDRs are not, because
# nothing outside this function needs them.
PODS_RANGE = "pods"
SERVICES_RANGE = "services"
SECONDARY_RANGES = {PODS_RANGE: "10.200.0.0/14", SERVICES_RANGE: "10.204.0.0/16"}

# Mirrors the XRD default, for renders that skip defaulting.
DEFAULT_MANAGEMENT_POLICIES = ["*"]

# GCP's rule for network and subnetwork names, which it enforces only at apply.
# https://cloud.google.com/compute/docs/reference/rest/v1/subnetworks/insert
NAME_PATTERN = re.compile(r"[a-z]([-a-z0-9]*[a-z0-9])?")
NAME_MAX_LENGTH = 63


def _valid_name(name: str) -> bool:
    return len(name) <= NAME_MAX_LENGTH and NAME_PATTERN.fullmatch(name) is not None


def _list(items: list[str]) -> str:
    """Format a list as [a, b], the form these error messages have always used."""
    return f"[{', '.join(items)}]"


def network_name(params: dict) -> str:
    """The network's GCP name, which is also its MR name unless it's adopted."""
    return (params.get("externalNames") or {}).get(NETWORK, params["id"])


def subnetwork_name(params: dict) -> str:
    """The subnetwork's GCP name."""
    return (params.get("externalNames") or {}).get(SUBNETWORK, derived_subnetwork_name(params))


def derived_subnetwork_name(params: dict) -> str:
    """The subnetwork's MR name, and its GCP name unless it's adopted."""
    return f"{params['id']}-subnetwork"


def validate(params: dict) -> list[str]:
    """Return the reasons these parameters would compose resources GCP rejects or that adopt
    nothing. Empty when they're fine.

    The XRD rejects empty externalNames values, so they aren't checked here.
    """
    errors: list[str] = []
    external_names = params.get("externalNames") or {}

    # An unknown key would create a duplicate instead of adopting.
    unknown = [k for k in external_names if k not in EXTERNAL_NAME_KEYS]
    if unknown:
        errors.append(
            f"spec.parameters.externalNames has unknown key(s) {_list(unknown)}; "
            f"valid keys for this Network are {_list(EXTERNAL_NAME_KEYS)}"
        )

    name = network_name(params)
    if not _valid_name(name):
        errors.append(
            f"spec.parameters.id yields network name '{name}', which is not a valid "
            "compute network name; a name is at most 63 characters, lowercase letters, numbers "
            "and hyphens, starts with a letter and ends with a letter or number, so adjust "
            "spec.parameters.id"
        )
        # The derived subnetwork name is then invalid for the same reason; one fix, one message.
        if NETWORK not in external_names:
            return errors

    # A subnetwork is name-as-identifier, so metadata.name is its GCP name unless it's adopted.
    derived = derived_subnetwork_name(params)
    if SUBNETWORK not in external_names and not _valid_name(derived):
        errors.append(
            f"spec.parameters.id yields derived name(s) ['{derived}'], which are not "
            "valid subnetwork names; the subnetwork is named '{id}-subnetwork' and a name is at "
            "most 63 characters, lowercase letters, numbers and hyphens, starting with a letter "
            "and ending with a letter or number, so keep spec.parameters.id at 52 characters or "
            "fewer"
        )

    return errors


def build(
    xr_name: str,
    namespace: str,
    params: dict,
    *,
    observed: dict | None = None,
) -> dict[str, BaseModel]:
    """Return the composed resources, as models, keyed by composition resource name.

    Both resources are always composed and depend only on the parameters, so xr_name, namespace
    and `observed` are accepted for the signature the GKE and database functions share but are
    not read: Crossplane labels composed resources with their XR and places them in its
    namespace. Call validate() first; build() assumes valid parameters.
    """
    external_names = params.get("externalNames") or {}

    def metadata(name: str, resource_name: str) -> metav1.ObjectMeta:
        annotations = None
        if resource_name in external_names:
            annotations = {EXTERNAL_NAME_ANNOTATION: external_names[resource_name]}
        return metav1.ObjectMeta(
            name=name,
            annotations=annotations,
            labels={NETWORK_ID_LABEL: params["id"]},
        )

    policies = params.get("managementPolicies") or DEFAULT_MANAGEMENT_POLICIES
    # Without a ProviderConfig name, leave providerConfigRef to the API server's default.
    provider_config_ref = None
    if params.get("providerConfigName"):
        provider_config_ref = {"kind": "ProviderConfig", "name": params["providerConfigName"]}

    return {
        NETWORK: networkv1beta1.Network(
            metadata=metadata(params["id"], NETWORK),
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
            metadata=metadata(derived_subnetwork_name(params), SUBNETWORK),
            spec=subnetworkv1beta1.Spec(
                managementPolicies=policies,
                providerConfigRef=provider_config_ref,
                forProvider=subnetworkv1beta1.ForProvider(
                    ipCidrRange=SUBNETWORK_CIDR,
                    region=params["region"],
                    networkSelector=subnetworkv1beta1.NetworkSelector(matchControllerRef=True),
                    privateIpGoogleAccess=True,
                    secondaryIpRange=[
                        subnetworkv1beta1.SecondaryIpRangeItem(ipCidrRange=cidr, rangeName=name)
                        for name, cidr in SECONDARY_RANGES.items()
                    ],
                ),
            ),
        ),
    }


def _at_provider(observed: dict, key: str) -> dict:
    return ((observed.get(key) or {}).get("status") or {}).get("atProvider") or {}


def status(params: dict, observed: dict | None = None) -> dict:
    """Return the XR status other domains read instead of selecting the composed resources.

    Names, region and ranges follow from the parameters and are published from the first
    reconcile. id and selfLink exist only once the provider has created or observed the object
    in GCP, so they're absent until then: consumers wait for both selfLinks before using the
    network. `observed` maps composition resource names to the composed resources as they exist.
    """
    observed = observed or {}

    def published(key: str) -> dict:
        at_provider = _at_provider(observed, key)
        return {f: at_provider[f] for f in ("id", "selfLink") if at_provider.get(f)}

    return {
        "vpc": {"name": network_name(params), **published(NETWORK)},
        "subnetwork": {
            "name": subnetwork_name(params),
            "region": params["region"],
            "ipCidrRange": SUBNETWORK_CIDR,
            **published(SUBNETWORK),
            "secondaryRanges": {"pods": PODS_RANGE, "services": SERVICES_RANGE},
        },
    }
