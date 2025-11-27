import models.io.upbound.gcpm.compute.v1beta1 as computev1beta1
import models.io.upbound.platform.gcp.v1alpha1 as platformgcpv1alpha1

oxr = platformgcpv1alpha1.Network{**option("params").oxr}
params = oxr.spec.parameters

providerConfigRefName = params.providerConfigName or None

_metadata = lambda name: str -> any {
    {
        annotations = {"krm.kcl.dev/composition-resource-name" = name}
        labels = {"networks.gcp.platform.upbound.io/network-id" = params.id}
    }
}

_defaults = {
    managementPolicies = params.managementPolicies or ["*"]
    if providerConfigRefName:
        providerConfigRef = {
            kind = "ProviderConfig"
            name = providerConfigRefName
        }
}

_items = [
    computev1beta1.Network{
        metadata = _metadata("network") | {
            name: params.id
        }
        spec = _defaults | {
            forProvider = {
                autoCreateSubnetworks = False
                routingMode = "REGIONAL"
            }
        }
    }
    computev1beta1.Subnetwork{
        metadata = _metadata("subnetwork")
        spec = _defaults | {
            forProvider = {
                ipCidrRange = "172.16.0.0/16"
                region = params.region
                networkSelector = {
                    matchControllerRef = True
                }
                privateIpGoogleAccess = True
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
        }
    }
]

items = _items
