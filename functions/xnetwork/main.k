
import models.io.upbound.gcp.compute.v1beta1 as computev1beta1
import models.io.upbound.gcp.compute.v1beta2 as computev1beta2
import models.io.upbound.gcp.v1alpha1 as gcpv1alpha1
import models.io.upbound.gcp.v1beta1 as gcpv1beta1
import models.k8s.apimachinery.pkg.apis.meta.v1 as metav1

oxr = option("params").oxr # observed composite resource
_ocds = option("params").ocds # observed composed resources
_dxr = option("params").dxr # desired composite resource
dcds = option("params").dcds # desired composed resources

_metadata = lambda name: str -> any {
    { annotations = { "krm.kcl.dev/composition-resource-name" = name }}
}

# Example to retrieve variables from "xr"; update as needed
# _region = "us-east-1"
# if oxr.spec?.parameters?.region:
#     _region = oxr.spec.parameters.region

_items = [
    computev1beta1.Network{
        metadata = _metadata("network") | {
            name = "ref-gcp-network-from-xr"
        }
        spec = {
            forProvider = {
                autoCreateSubnetworks = False
            }
        }
    }
]

#          - name: network
#            base:
#              apiVersion: compute.gcp.upbound.io/v1beta1
#              kind: Network
#              spec:
#                forProvider:
#                  autoCreateSubnetworks: false
#                  routingMode: REGIONAL
#            patches:
#              - type: PatchSet
#                patchSetName: providerConfigRef
#              - type: PatchSet
#                patchSetName: deletionPolicy
#              - type: FromCompositeFieldPath
#                fromFieldPath: spec.parameters.id
#                toFieldPath: metadata.name
#              - type: FromCompositeFieldPath
#                fromFieldPath: spec.parameters.id
#                toFieldPath: metadata.labels[networks.gcp.platform.upbound.io/network-id]

items = _items

