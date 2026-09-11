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

# An empty value is not adoption: it overrides the external-name a resource
# hardcodes and crossplane-runtime then falls back to the generated
# metadata.name, creating a differently named cloud object instead of adopting.
_emptyExternalNames = ["'{}'".format(k) for k, v in _externalNames if not v]

assert len(_emptyExternalNames) == 0, "spec.parameters.externalNames has an empty value for key(s) ${_emptyExternalNames}; an empty external-name adopts nothing and drops back to the generated resource name, so omit the key instead"

# The network's GCP name is its metadata.name, which is params.id in either
# naming mode, unless externalNames replaces it. Validate whichever value lands:
# a compute network name is at most 63 characters and RFC1035-shaped, and GCP
# rejects a malformed one only once the provider calls the API. The subnetwork
# is checked further down, where the Deterministic suffix is applied.
_networkName = _externalNames["network"] if "network" in _externalNames else params.id

assert len(_networkName) <= 63 and regex.match(_networkName, "^[a-z]([-a-z0-9]*[a-z0-9])?$"), "spec.parameters.id yields network name '${_networkName}', which is not a valid compute network name; a name is at most 63 characters, lowercase letters, numbers and hyphens, starts with a letter and ends with a letter or number, so adjust spec.parameters.id"

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

# Subnetwork names live in a per-project per-region collection of their own, so
# the suffix is not needed to avoid the network's name; it is there so the GCP
# object says which composed resource it is.
_subnetworkStableName = "{}-subnetwork".format(params.id)

# A subnetwork name is at most 63 characters, lowercase letters, numbers and
# hyphens only, starting with a letter and ending with a letter or number
# (https://cloud.google.com/compute/docs/reference/rest/v1/subnetworks/insert).
# GCP rejects a malformed name only once the provider calls the API, long after
# apply, so reject it here instead of letting it render.
_invalidStableNames = [
    "'{}'".format(n) for n in [_subnetworkStableName]
    if _deterministic and not (len(n) <= 63 and regex.match(n, "^[a-z]([-a-z0-9]*[a-z0-9])?$"))
]

assert len(_invalidStableNames) == 0, "spec.parameters.naming is Deterministic but the derived name(s) ${_invalidStableNames} are not valid subnetwork names; a name is at most 63 characters, lowercase letters, numbers and hyphens, starts with a letter and ends with a letter or number, so adjust spec.parameters.id"

_named = lambda compositionName: str, stableName: str -> any {
    _metadata(compositionName) | {
        if _deterministic:
            name = stableName
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
        metadata = _named("subnetwork", _subnetworkStableName)
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
