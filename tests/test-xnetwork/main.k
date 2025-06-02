import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1
import models.io.upbound.gcp.compute.v1beta1 as computev1beta1
import models.io.upbound.platform.gcp.v1alpha1 as platformgcpv1alpha1

_items = [
    metav1alpha1.CompositionTest {
        metadata.name: "test-network"
        spec = {
            assertResources: [
                platformgcpv1alpha1.XNetwork{
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
                        generateName = "ref-gcp-network-"
                        labels = {
                            "crossplane.io/composite" = "ref-gcp-network"
                            "networks.gcp.platform.upbound.io/network-id" = "ref-gcp-network-from-xr"
                        }
                        name = "ref-gcp-network-from-xr"
                        ownerReferences = [
                            {
                                apiVersion = "gcp.platform.upbound.io/v1alpha1"
                                blockOwnerDeletion = True
                                controller = True
                                kind = "XNetwork"
                                name = "ref-gcp-network"
                                uid = ""
                            }
                        ]
                    }
                    spec = {
                        forProvider = {
                            autoCreateSubnetworks = False
                            routingMode = "REGIONAL"
                        }
                    }
                }
                computev1beta1.Subnetwork{
                    metadata = {
                        generateName = "ref-gcp-network-"
                        labels = {
                            "crossplane.io/composite" = "ref-gcp-network"
                            "networks.gcp.platform.upbound.io/network-id" = "ref-gcp-network-from-xr"
                        }
                        ownerReferences = [
                            {
                                apiVersion = "gcp.platform.upbound.io/v1alpha1"
                                blockOwnerDeletion = True
                                controller = True
                                kind = "XNetwork"
                                name = "ref-gcp-network"
                                uid = ""
                            }
                        ]
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
                    }
                }
            ]
            compositionPath: "apis/xnetworks/composition.yaml"
            xrPath: "examples/network-xr.yaml"
            xrdPath: "apis/xnetworks/definition.yaml"
            timeoutSeconds: 60
            validate: False
        }
    }
]
items = _items
