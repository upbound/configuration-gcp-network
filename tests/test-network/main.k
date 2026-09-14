import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1
import models.io.upbound.gcpm.compute.v1beta1 as computev1beta1
import models.io.upbound.platform.gcp.v1alpha1 as platformgcpv1alpha1

_xr = platformgcpv1alpha1.Network{
    metadata: {
        name: "ref-gcp-network"
        namespace: "default"
    }
    spec: {
        parameters: {
            id: "ref-gcp-network-from-xr"
            region: "us-west2"
        }
    }
}

# An injected external-name observes the existing GCP object instead of
# creating a duplicate, whatever the composed resource is called.
_xrExternalNames = platformgcpv1alpha1.Network{
    metadata: {
        name: "ref-gcp-network"
        namespace: "default"
    }
    spec: {
        parameters: {
            id: "ref-gcp-network-from-xr"
            region: "us-west2"
            externalNames: {
                network: "adopted-network"
                subnetwork: "adopted-subnetwork"
            }
        }
    }
}

_items = [
    metav1alpha1.CompositionTest {
        metadata.name: "test-network"
        spec = {
            assertResources: [
                platformgcpv1alpha1.Network{
                    metadata = {
                        name = "ref-gcp-network"
                    }
                    spec = {
                        parameters = {
                            id = "ref-gcp-network-from-xr"
                            region = "us-west2"
                        }
                    }
                }
                computev1beta1.Network{
                    metadata = {
                        annotations = {
                            "crossplane.io/composition-resource-name" = "network"
                        }
                        labels = {
                            "crossplane.io/composite" = "ref-gcp-network"
                            "networks.gcp.platform.upbound.io/network-id" = "ref-gcp-network-from-xr"
                        }
                        name = "ref-gcp-network-from-xr"
                    }
                    spec = {
                        forProvider = {
                            autoCreateSubnetworks = False
                            routingMode = "REGIONAL"
                        }
                        managementPolicies = ["*"]
                        providerConfigRef = {
                            kind = "ProviderConfig"
                            name = "default"
                        }
                    }
                }
                computev1beta1.Subnetwork{
                    metadata = {
                        annotations = {
                            "crossplane.io/composition-resource-name" = "subnetwork"
                        }
                        name = "ref-gcp-network-from-xr-subnetwork"
                        labels = {
                            "crossplane.io/composite" = "ref-gcp-network"
                            "networks.gcp.platform.upbound.io/network-id" = "ref-gcp-network-from-xr"
                        }
                    }
                    spec = {
                        forProvider = {
                            ipCidrRange = "172.16.0.0/16"
                            networkSelector = {
                                matchControllerRef = True
                            }
                            privateIpGoogleAccess = True
                            region = "us-west2"
                            secondaryIpRange = [
                                {
                                    ipCidrRange = "10.200.0.0/14"
                                    rangeName = "pods"
                                }
                                {
                                    ipCidrRange = "10.204.0.0/16"
                                    rangeName = "services"
                                }
                            ]
                        }
                        managementPolicies = ["*"]
                        providerConfigRef = {
                            kind = "ProviderConfig"
                            name = "default"
                        }
                    }
                }
            ]
            compositionPath: "apis/networks/composition.yaml"
            xrPath: "examples/network-xr.yaml"
            xrdPath: "apis/networks/definition.yaml"
            timeoutSeconds: 60
            validate: False
        }
    }
    metav1alpha1.CompositionTest {
        metadata.name: "test-network-derived-names"
        spec = {
            assertResources: [
                computev1beta1.Network{
                    metadata = {
                        annotations = {
                            "crossplane.io/composition-resource-name" = "network"
                        }
                        name = "ref-gcp-network-from-xr"
                    }
                    spec = {
                        forProvider = {}
                    }
                }
                computev1beta1.Subnetwork{
                    metadata = {
                        annotations = {
                            "crossplane.io/composition-resource-name" = "subnetwork"
                        }
                        name = "ref-gcp-network-from-xr-subnetwork"
                    }
                    spec = {
                        forProvider = {
                            region = "us-west2"
                        }
                    }
                }
            ]
            compositionPath: "apis/networks/composition.yaml"
            xrdPath: "apis/networks/definition.yaml"
            timeoutSeconds: 60
            validate: False
            xr: _xr
        }
    }
    metav1alpha1.CompositionTest {
        metadata.name: "test-network-external-names"
        spec = {
            assertResources: [
                computev1beta1.Network{
                    metadata = {
                        annotations = {
                            "crossplane.io/composition-resource-name" = "network"
                            "crossplane.io/external-name" = "adopted-network"
                        }
                        name = "ref-gcp-network-from-xr"
                    }
                    spec = {
                        forProvider = {}
                    }
                }
                computev1beta1.Subnetwork{
                    metadata = {
                        annotations = {
                            "crossplane.io/composition-resource-name" = "subnetwork"
                            "crossplane.io/external-name" = "adopted-subnetwork"
                        }
                        name = "ref-gcp-network-from-xr-subnetwork"
                    }
                    spec = {
                        forProvider = {
                            region = "us-west2"
                        }
                    }
                }
            ]
            compositionPath: "apis/networks/composition.yaml"
            xrdPath: "apis/networks/definition.yaml"
            timeoutSeconds: 60
            validate: False
            xr: _xrExternalNames
        }
    }
]
items = _items
