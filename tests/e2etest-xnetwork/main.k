import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1
import models.io.upbound.gcp.v1beta1 as gcpv1beta1
import models.io.upbound.platform.gcp.v1alpha1 as platformgcpv1alpha1

_items = [
    metav1alpha1.E2ETest{
        metadata.name: "xnetwork"
        spec= {
            crossplane.autoUpgrade.channel: "Rapid"
            defaultConditions: ["Ready"]
            manifests: [
                platformgcpv1alpha1.XNetwork{
                    metadata.name: "configuration-gcp-network-e2e"
                    spec: {
                        parameters: {
                            id: "configuration-gcp-network-e2e"
                            region: "us-west2"
                        }
                    }
                }
            ]
            extraResources: [
                gcpv1beta1.ProviderConfig{
                    metadata.name: "default"
                    spec: {
                        projectID: "crossplane-playground"
                        credentials: {
                            source: "Upbound"
                            upbound: {
                                federation: {
                                    providerID: "projects/283222062215/locations/global/workloadIdentityPools/solutions-upbound-oidc-pool/providers/solutions-u5d-oidc-pool"
                                    serviceAccount: "solutions-u5d-service-account@crossplane-playground.iam.gserviceaccount.com"
                                }
                            }
                        }
                    }
                }
            ]
            skipDelete: False
            timeoutSeconds: 4500
        }
    }
]

items= _items
