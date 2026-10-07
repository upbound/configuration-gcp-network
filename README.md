# configuration-gcp-network

GCP Network Configuration is reusable Configuration designed to be primarily used in higher level Configurations.

## Upgrading to provider-gcp v3

This configuration requires provider-gcp `>=v3.0.5, <v4.0.0`, which removes the
deprecated `v1beta1` API versions.

- New control planes can install it directly.
- Control planes on provider-gcp below v2.6 must first install the previous
  release of this configuration, which requires provider-gcp
  `>=v2.6.0, <v3.0.0`, and let the providers reach v2.6.
- Before upgrading from v2.6, follow the provider's
  [storage version migration](https://github.com/crossplane-contrib/provider-upjet-gcp/releases/tag/v3.0.0):
  apply its migration `DeploymentRuntimeConfig` to each sub-provider this
  configuration installs (provider-gcp-compute), not to `provider-family-gcp`.
