"""Generate the Network CompositionTests and print them as YAML."""

import copy

import yaml
from models.io.k8s.apimachinery.pkg.apis.meta import v1 as k8s
from models.io.upbound.dev.meta.compositiontest import v1alpha1 as compositiontest

COMPOSITION = "apis/networks/composition.yaml"
XRD = "apis/networks/definition.yaml"

NAME = "ref-gcp-network"
ID = "ref-gcp-network-from-xr"
COMPUTE = "compute.gcp.m.upbound.io/v1beta1"

LABELS = {
    "crossplane.io/composite": NAME,
    "networks.gcp.platform.upbound.io/network-id": ID,
}
PROVIDER_CONFIG_REF = {"kind": "ProviderConfig", "name": "default"}

# The XRD's defaults, which the API server fills in.
DEFAULTS = {"managementPolicies": ["*"], "providerConfigName": "default"}

XR = {
    "apiVersion": "gcp.platform.upbound.io/v1alpha1",
    "kind": "Network",
    "metadata": {"name": NAME, "namespace": "default"},
    "spec": {"parameters": {"id": ID, "region": "us-west2", **DEFAULTS}},
}


def xr(**parameters) -> dict:
    out = copy.deepcopy(XR)
    out["spec"]["parameters"].update(parameters)
    return out


def annotations(resource_name: str, external_name: str | None = None) -> dict:
    out = {"crossplane.io/composition-resource-name": resource_name}
    if external_name:
        out["crossplane.io/external-name"] = external_name
    return out


def names(network: str | None = None, subnetwork: str | None = None) -> list[dict]:
    """Assert the composed resources' names and identifying annotations only."""
    return [
        {
            "apiVersion": COMPUTE,
            "kind": "Network",
            "metadata": {"name": ID, "annotations": annotations("network", network)},
            "spec": {"forProvider": {}, "managementPolicies": ["*"]},
        },
        {
            "apiVersion": COMPUTE,
            "kind": "Subnetwork",
            "metadata": {
                "name": f"{ID}-subnetwork",
                "annotations": annotations("subnetwork", subnetwork),
            },
            "spec": {"forProvider": {"region": "us-west2"}, "managementPolicies": ["*"]},
        },
    ]


def test(name: str, **spec) -> compositiontest.CompositionTest:
    return compositiontest.CompositionTest(
        metadata=k8s.ObjectMeta(name=name),
        spec=compositiontest.Spec(
            compositionPath=COMPOSITION,
            xrdPath=XRD,
            timeoutSeconds=60,
            validate=True,
            **spec,
        ),
    )


tests = [
    # The example composes a custom-mode network and one subnetwork with GKE's secondary ranges.
    test(
        "test-network",
        xrPath="examples/network-xr.yaml",
        assertResources=[
            {
                "apiVersion": "gcp.platform.upbound.io/v1alpha1",
                "kind": "Network",
                "metadata": {"name": NAME},
                "spec": {"parameters": {"id": ID, "region": "us-west2", **DEFAULTS}},
            },
            {
                "apiVersion": COMPUTE,
                "kind": "Network",
                "metadata": {"name": ID, "annotations": annotations("network"), "labels": LABELS},
                "spec": {
                    "forProvider": {"autoCreateSubnetworks": False, "routingMode": "REGIONAL"},
                    "managementPolicies": ["*"],
                    "providerConfigRef": PROVIDER_CONFIG_REF,
                },
            },
            {
                "apiVersion": COMPUTE,
                "kind": "Subnetwork",
                "metadata": {
                    "name": f"{ID}-subnetwork",
                    "annotations": annotations("subnetwork"),
                    "labels": LABELS,
                },
                "spec": {
                    "forProvider": {
                        "ipCidrRange": "172.16.0.0/16",
                        "networkSelector": {"matchControllerRef": True},
                        "privateIpGoogleAccess": True,
                        "region": "us-west2",
                        "secondaryIpRange": [
                            {"ipCidrRange": "10.200.0.0/14", "rangeName": "pods"},
                            {"ipCidrRange": "10.204.0.0/16", "rangeName": "services"},
                        ],
                    },
                    "managementPolicies": ["*"],
                    "providerConfigRef": PROVIDER_CONFIG_REF,
                },
            },
        ],
    ),
    # Composed resources are named from spec.parameters.id.
    test("test-network-derived-names", xr=xr(), assertResources=names()),
    # An injected external-name observes the existing GCP object instead of creating a
    # duplicate, whatever the composed resource is called.
    test(
        "test-network-external-names",
        xr=xr(externalNames={"network": "adopted-network", "subnetwork": "adopted-subnetwork"}),
        assertResources=names(network="adopted-network", subnetwork="adopted-subnetwork"),
    ),
]

# The test runner expects an "items" array, one entry per test.
output = {"items": [t.model_dump(by_alias=True, exclude_none=True) for t in tests]}
print(yaml.dump(output))
