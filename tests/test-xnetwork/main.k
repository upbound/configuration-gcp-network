
import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1
import models.io.upbound.gcp.compute.v1beta1 as computev1beta1
import models.io.upbound.gcp.compute.v1beta2 as computev1beta2
import models.io.upbound.gcp.v1alpha1 as gcpv1alpha1
import models.io.upbound.gcp.v1beta1 as gcpv1beta1
import models.io.upbound.platform.gcp.v1alpha1 as platformgcpv1alpha1
import models.k8s.apimachinery.pkg.apis.meta.v1 as metav1


_items = [
    metav1alpha1.CompositionTest{
        metadata.name: ""
        spec= {
            assertResources: [
                {
                    apiVersion = "gcp.platform.upbound.io/v1alpha1"
                    kind = "XNetwork"
                    metadata = {
                        annotations = {
                            "render.crossplane.io/composition-path" = "apis/default/composition.yaml"
                            "render.crossplane.io/function-path" = "examples/functions.yaml"
                        }
                        name = "ref-gcp-network"
                    }
                    spec = {
                        parameters = {
                            id = "ref-gcp-network-from-xr"
                            region = "us-west2"
                        }
                    }
                    status = {
                        conditions = [
                            {
                                lastTransitionTime = "2024-01-01T00:00:00Z"
                                message = "Unready resources: network, subnetwork"
                                reason = "Creating"
                                status = "False"
                                $type = "Ready"
                            }
                        ]
                    }
                }
                {
                    apiVersion = "compute.gcp.upbound.io/v1beta1"
                    kind = "Network"
                    metadata = {
                        annotations = {
                            "crossplane.io/composition-resource-name" = "network"
                        }
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
                {
                    apiVersion = "compute.gcp.upbound.io/v1beta1"
                    kind = "Subnetwork"
                    metadata = {
                        annotations = {
                            "crossplane.io/composition-resource-name" = "subnetwork"
                        }
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
            xrdPath: "apis/definition.yaml"
            timeoutSeconds: 60
            validate: False
        }
    }
]
items= _items
