"""Generate the Network E2ETest and print it as YAML."""

import yaml
from models.io.k8s.apimachinery.pkg.apis.meta import v1 as k8s
from models.io.upbound.dev.meta.e2etest import v1alpha1 as e2etest

NAMESPACE = "default"
NETWORK_ID = "configuration-gcp-network-e2e"

test = e2etest.E2ETest(
    metadata=k8s.ObjectMeta(name="e2e-test-network"),
    spec=e2etest.Spec(
        crossplane=e2etest.Crossplane(
            autoUpgrade=e2etest.AutoUpgrade(channel="None"),
            version="2.0.2-up.5",
        ),
        defaultConditions=["Ready"],
        manifests=[
            {
                "apiVersion": "gcp.platform.upbound.io/v1alpha1",
                "kind": "Network",
                "metadata": {"name": NETWORK_ID, "namespace": NAMESPACE},
                "spec": {
                    "parameters": {
                        "id": NETWORK_ID,
                        "region": "us-west2",
                        # The XRD's defaults, which the API server fills in.
                        "managementPolicies": ["*"],
                        "providerConfigName": "default",
                    },
                },
            },
        ],
        extraResources=[
            {
                "apiVersion": "gcp.m.upbound.io/v1beta1",
                "kind": "ProviderConfig",
                "metadata": {"name": "default", "namespace": NAMESPACE},
                "spec": {
                    "projectID": "crossplane-playground",
                    "credentials": {
                        "source": "Upbound",
                        "upbound": {
                            "federation": {
                                "providerID": "projects/283222062215/locations/global/workloadIdentityPools/solutions-upbound-oidc-pool/providers/solutions-u5d-oidc-pool",
                                "serviceAccount": "solutions-u5d-service-account@crossplane-playground.iam.gserviceaccount.com",
                            },
                        },
                    },
                },
            },
        ],
        # If True, skip cleanup of test resources and control plane after test
        # completion. Useful for debugging and inspecting test state. Defaults to
        # False.
        skipDelete=False,
        timeoutSeconds=4500,
    ),
)

# The test runner expects an "items" array, one entry per test.
output = {"items": [test.model_dump(by_alias=True, exclude_none=True)]}
print(yaml.dump(output))
