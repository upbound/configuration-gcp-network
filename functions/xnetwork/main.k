import models.io.upbound.gcp.compute.v1beta1 as computev1beta1
import models.io.upbound.platform.gcp.v1alpha1 as platformgcpv1alpha1

oxr = platformgcpv1alpha1.XNetwork{**option("params").oxr} # observed composite resource
params = oxr.spec.parameters

_metadata = lambda name: str -> any {
    {
        annotations = {"krm.kcl.dev/composition-resource-name" = name}
        labels = {"networks.gcp.platform.upbound.io/network-id" = params.id}
    }
}

# Helper function to add common spec fields
_add_common_spec_fields = lambda spec: any -> any {
    spec | {
        deletionPolicy = params.deletionPolicy
        providerConfigRef.name = params.providerConfigName
    }
}

_items = [
computev1beta1.Network{
    metadata = _metadata("network") | {
        name: oxr.spec.parameters.id
    }
    spec: {
        forProvider: {
            autoCreateSubnetworks: False
            routingMode: "REGIONAL"
        }
    }
}
computev1beta1.Subnetwork{
    metadata = _metadata("subnetwork")
    spec:{
        forProvider: {
            ipCidrRange: "172.16.0.0/16"
            region: params.region
            networkSelector: {
                matchControllerRef: True
            }
            privateIpGoogleAccess: True
            secondaryIpRange: [
                {
                    ipCidrRange: "10.200.0.0/14"
                    rangeName: "pods"
                },
                {
                    ipCidrRange: "10.204.0.0/16"
                    rangeName: "services"
                },
            ]
        }
    }
}
]

items = _items
