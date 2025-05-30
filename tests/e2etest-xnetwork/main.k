
import models.io.upbound.dev.meta.v1alpha1 as metav1alpha1
import models.io.upbound.gcp.compute.v1beta1 as computev1beta1
import models.io.upbound.gcp.compute.v1beta2 as computev1beta2
import models.io.upbound.gcp.v1alpha1 as gcpv1alpha1
import models.io.upbound.gcp.v1beta1 as gcpv1beta1
import models.io.upbound.platform.gcp.v1alpha1 as platformgcpv1alpha1
import models.k8s.apimachinery.pkg.apis.meta.v1 as metav1


_items = [
    metav1alpha1.E2ETest{
        metadata.name: ""
        spec= {
            crossplane.autoUpgrade.channel: "Rapid"
            defaultConditions: ["Ready"]
            manifests: []
            extraResources: []
            skipDelete: False
            timeoutSeconds: 4500
        }
    }
]
items= _items