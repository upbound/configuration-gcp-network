import models.io.upbound.gcpm.compute.v1beta1 as computev1beta1
import models.io.upbound.platform.gcp.v1alpha1 as platformgcpv1alpha1

import regex

oxr = platformgcpv1alpha1.Network{**option("params").oxr}
params = oxr.spec.parameters

providerConfigRefName = params.providerConfigName or None

_externalNames = params.externalNames or {}

# Every composition-resource-name this function can emit.
_externalNameKeys = ["network", "subnetwork"]

# Fail loudly on an unknown key. Silently ignoring one would leave that resource
# unadopted and create a duplicate in GCP, the exact failure adoption prevents.
_unknownExternalNames = [k for k in _externalNames if k not in _externalNameKeys]

assert len(_unknownExternalNames) == 0, "spec.parameters.externalNames has unknown key(s) ${_unknownExternalNames}; valid keys for this Network are ${_externalNameKeys}"

# Every composed resource routes its annotations through here, so injecting the
# external-name at this single point covers all of them.
_metadata = lambda name: str -> any {
    {
        annotations = {
            "krm.kcl.dev/composition-resource-name" = name
            if name in _externalNames:
                "crossplane.io/external-name" = _externalNames[name]
        }
        labels = {"networks.gcp.platform.upbound.io/network-id" = params.id}
    }
}

# Deterministic naming, opt-in. A GCP subnetwork is a name-as-identifier type,
# so metadata.name IS its GCP identifier and setting it makes adoption possible
# without any GCP query. The network is named from id unconditionally and needs
# no flag; gating it would rename it for every consumer that already runs this
# configuration.
_deterministic = (params.naming or "Generated") == "Deterministic"

_named = lambda compositionName: str, stableName: str -> any {
    _metadata(compositionName) | {
        if _deterministic:
            name = stableName
    }
}

# Subnetwork names live in a per-project per-region collection of their own, so
# the suffix is not needed to avoid the network's name; it is there so the GCP
# object says which composed resource it is.
_subnetworkName = "{}-subnetwork".format(params.id)

# GCP rejects a malformed subnetwork name only once the provider calls the API,
# long after apply, so check it here instead.
assert not _deterministic or regex.match(_subnetworkName, r"^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$"), "spec.parameters.id '${params.id}' yields subnetwork name '${_subnetworkName}', which GCP will reject; a subnetwork name is 1-63 characters of lowercase alphanumerics or '-', starting with a letter and ending with a letter or digit"

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
        metadata = _named("subnetwork", _subnetworkName)
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
