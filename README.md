# configuration-gcp-network

GCP Network Configuration is reusable Configuration designed to be primarily used in higher level Configurations.

A `Network` composes a custom-mode VPC network and one regional subnetwork with
secondary ranges for GKE Pods and Services, named from `spec.parameters.id`.
Either can adopt an existing GCP object through `spec.parameters.externalNames`.

## Published status

A `Network` publishes what other domains need in its status, so they can use it
without knowing how it's built:

```yaml
status:
  vpc:
    name: ref-gcp-network                 # GCP name; from the first reconcile
    id: projects/<project>/global/networks/ref-gcp-network           # once created
    selfLink: https://www.googleapis.com/compute/v1/projects/...     # once created
  subnetwork:
    name: ref-gcp-network-subnetwork      # GCP name; from the first reconcile
    region: us-west2
    ipCidrRange: 172.16.0.0/16
    id: projects/<project>/regions/us-west2/subnetworks/ref-gcp-network-subnetwork  # once created
    selfLink: https://www.googleapis.com/compute/v1/projects/...     # once created
    secondaryRanges:
      pods: pods                          # secondary range names for GKE
      services: services
```

`name`, `region`, `ipCidrRange` and `secondaryRanges` are set from the spec on
the first reconcile. `id` and `selfLink` appear only once the provider has
created (or adopted) the object in GCP: wait for both `selfLink`s before using
the Network.

## Referencing a Network

Consumers such as
[configuration-gcp-gke](https://github.com/upbound/configuration-gcp-gke) and
[configuration-gcp-database](https://github.com/upbound/configuration-gcp-database)
should reference a Network by name through their `spec.parameters.networkRef.name`,
which must be a `Network` in the same namespace. Their functions read this
status and wire their resources from it by value, rather than selecting this
Network's composed resources.

The composed resources still carry the
`networks.gcp.platform.upbound.io/network-id: <id>` label, so consumers that
select them by `spec.parameters.id` keep working, but that ties them to how this
Network is built. New consumers should use `networkRef.name` and the published
status.

## Upgrading to provider-gcp v3

This configuration requires provider-gcp `>=v3.0.5, <v4.0.0`, which removes the
deprecated `v1beta1` API versions.

- New control planes can install it directly.
- Control planes running provider-gcp below v2.6 must upgrade those providers to
  v2.6 first, then follow the provider's
  [storage version migration](https://github.com/crossplane-contrib/provider-upjet-gcp/releases/tag/v3.0.0):
  apply its migration `DeploymentRuntimeConfig` to each sub-provider this
  configuration installs (provider-gcp-compute), not to `provider-family-gcp`.
  Alternatively, rebuild the control plane.
