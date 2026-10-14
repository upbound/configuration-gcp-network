"""Unit tests for the composed resources, the published status and validation.

These cover what the offline CompositionTests cannot express: the absence of a field or resource
(assertResources only matches what exists), and every validate() error.
"""

import asyncio

import pytest
from crossplane.function import resource
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from function import core, fn
from function.serialize import to_dict

ID = "net"
PARAMS = {
    "id": ID,
    "region": "us-west2",
    "managementPolicies": ["*"],
    "providerConfigName": "default",
}

NETWORK_ID = f"projects/p/global/networks/{ID}"
NETWORK_SELF_LINK = f"https://www.googleapis.com/compute/v1/{NETWORK_ID}"
SUBNETWORK_ID = f"projects/p/regions/us-west2/subnetworks/{ID}-subnetwork"
SUBNETWORK_SELF_LINK = f"https://www.googleapis.com/compute/v1/{SUBNETWORK_ID}"


def params(**overrides) -> dict:
    return {**PARAMS, **overrides}


def build(**overrides) -> dict[str, dict]:
    """Composed resources serialized exactly as fn.py sends them."""
    return {k: to_dict(v) for k, v in core.build("xr", "ns", params(**overrides)).items()}


def observed(network: dict | None = None, subnetwork: dict | None = None) -> dict:
    """Observed composed resources with the given status.atProvider, keyed like fn.py's."""
    out = {}
    for key, at_provider in ((core.NETWORK, network), (core.SUBNETWORK, subnetwork)):
        if at_provider is not None:
            out[key] = {"metadata": {"name": key}, "status": {"atProvider": at_provider}}
    return out


CREATED = observed(
    network={"id": NETWORK_ID, "selfLink": NETWORK_SELF_LINK},
    subnetwork={"id": SUBNETWORK_ID, "selfLink": SUBNETWORK_SELF_LINK},
)


class TestBuild:
    def test_composes_a_network_and_a_subnetwork(self):
        assert list(build()) == [core.NETWORK, core.SUBNETWORK]

    def test_composed_set_does_not_depend_on_observed_state(self):
        bare = core.build("xr", "ns", params())
        seen = core.build("xr", "ns", params(), observed=CREATED)
        assert {k: to_dict(v) for k, v in bare.items()} == {k: to_dict(v) for k, v in seen.items()}

    def test_resources_are_named_from_id(self):
        resources = build()
        assert resources[core.NETWORK]["metadata"]["name"] == ID
        assert resources[core.SUBNETWORK]["metadata"]["name"] == f"{ID}-subnetwork"

    def test_resources_carry_the_network_id_label_existing_consumers_select_by(self):
        for name, r in build().items():
            assert r["metadata"]["labels"] == {core.NETWORK_ID_LABEL: ID}, name

    def test_no_external_name_annotation_unless_adopting(self):
        for name, r in build().items():
            assert "annotations" not in r["metadata"], name

    def test_external_names_annotate_without_renaming(self):
        resources = build(externalNames={"network": "old-net", "subnetwork": "old-sub"})
        assert resources[core.NETWORK]["metadata"]["name"] == ID
        assert resources[core.NETWORK]["metadata"]["annotations"] == {
            core.EXTERNAL_NAME_ANNOTATION: "old-net"
        }
        assert resources[core.SUBNETWORK]["metadata"]["annotations"] == {
            core.EXTERNAL_NAME_ANNOTATION: "old-sub"
        }

    def test_no_provider_config_ref_without_a_name(self):
        for name, r in build(providerConfigName="").items():
            assert "providerConfigRef" not in r["spec"], name

    def test_empty_management_policies_default_to_all(self):
        for name, r in build(managementPolicies=[]).items():
            assert r["spec"]["managementPolicies"] == ["*"], name

    def test_subnetwork_selects_its_own_network(self):
        # By controller ref, never by name: an explicit ref has no ownership check.
        fp = build()[core.SUBNETWORK]["spec"]["forProvider"]
        assert fp["networkSelector"] == {"matchControllerRef": True}
        assert "networkRef" not in fp
        assert "network" not in fp

    def test_secondary_ranges_carry_the_names_status_publishes(self):
        ranges = build()[core.SUBNETWORK]["spec"]["forProvider"]["secondaryIpRange"]
        published = core.status(params())["subnetwork"]["secondaryRanges"]
        assert [r["rangeName"] for r in ranges] == [published["pods"], published["services"]]


class TestStatus:
    def test_before_anything_is_observed_only_spec_derived_fields_are_published(self):
        assert core.status(params()) == {
            "vpc": {"name": ID},
            "subnetwork": {
                "name": f"{ID}-subnetwork",
                "region": "us-west2",
                "ipCidrRange": "172.16.0.0/16",
                "secondaryRanges": {"pods": "pods", "services": "services"},
            },
        }

    def test_once_created_ids_and_self_links_are_published(self):
        out = core.status(params(), CREATED)
        assert out["vpc"] == {"name": ID, "id": NETWORK_ID, "selfLink": NETWORK_SELF_LINK}
        assert out["subnetwork"]["id"] == SUBNETWORK_ID
        assert out["subnetwork"]["selfLink"] == SUBNETWORK_SELF_LINK

    def test_an_observed_resource_without_at_provider_publishes_nothing_from_it(self):
        # Composed but not yet created by the provider: consumers must keep waiting.
        out = core.status(params(), {core.NETWORK: {"metadata": {"name": ID}}})
        assert "selfLink" not in out["vpc"]
        assert "id" not in out["vpc"]

    def test_each_resource_publishes_independently(self):
        out = core.status(params(), observed(network={"id": NETWORK_ID}))
        assert out["vpc"]["id"] == NETWORK_ID
        assert "selfLink" not in out["vpc"]
        assert "id" not in out["subnetwork"]
        assert "selfLink" not in out["subnetwork"]

    def test_empty_strings_are_not_published(self):
        out = core.status(params(), observed(network={"id": "", "selfLink": ""}))
        assert out["vpc"] == {"name": ID}

    def test_names_follow_external_names(self):
        out = core.status(params(externalNames={"network": "old-net", "subnetwork": "old-sub"}))
        assert out["vpc"]["name"] == "old-net"
        assert out["subnetwork"]["name"] == "old-sub"

    def test_status_matches_the_xrd_schema(self):
        from models.io.upbound.platform.gcp.network import v1alpha1 as platformv1alpha1

        # The generated model ignores unknown fields, so compare the round trip.
        out = core.status(params(), CREATED)
        assert to_dict(platformv1alpha1.Status(**out)) == out


class TestValidate:
    def test_valid_parameters(self):
        assert core.validate(params()) == []

    def test_unknown_external_name_key(self):
        errors = core.validate(params(externalNames={"bogus": "x", "network": "ok"}))
        assert errors == [
            (
                "spec.parameters.externalNames has unknown key(s) [bogus]; "
                "valid keys for this Network are [network, subnetwork]"
            )
        ]

    def test_invalid_id_reports_the_network_name_once(self):
        errors = core.validate(params(id="Bad_ID"))
        assert len(errors) == 1
        assert errors[0].startswith("spec.parameters.id yields network name 'Bad_ID'")

    def test_invalid_adopted_network_name(self):
        errors = core.validate(params(externalNames={"network": "Bad_Name"}))
        assert errors[0].startswith("spec.parameters.id yields network name 'Bad_Name'")

    def test_id_too_long_for_the_derived_subnetwork_name(self):
        errors = core.validate(params(id="a" * 53))
        assert len(errors) == 1
        assert f"['{'a' * 53}-subnetwork']" in errors[0]
        assert "52 characters or fewer" in errors[0]

    def test_id_at_the_limit(self):
        assert core.validate(params(id="a" * 52)) == []

    def test_adopted_subnetwork_lifts_the_derived_name_limit(self):
        assert core.validate(params(id="a" * 53, externalNames={"subnetwork": "s"})) == []

    def test_errors_from_independent_causes_are_all_reported(self):
        errors = core.validate(params(id="a" * 53, externalNames={"bogus": "x"}))
        assert len(errors) == 2


def run(xr: dict, observed_resources: dict | None = None) -> fnv1.RunFunctionResponse:
    req = fnv1.RunFunctionRequest(observed=fnv1.State(composite=fnv1.Resource()))
    resource.update(req.observed.composite, xr)
    for name, r in (observed_resources or {}).items():
        resource.update(req.observed.resources[name], r)
    return asyncio.run(fn.FunctionRunner().RunFunction(req, None))


XR = {
    "apiVersion": "gcp.platform.upbound.io/v1alpha1",
    "kind": "Network",
    "metadata": {"name": "xr", "namespace": "ns"},
    "spec": {"parameters": PARAMS},
}


class TestFunction:
    def test_publishes_status_on_the_composite(self):
        rsp = run(XR, CREATED)
        out = resource.struct_to_dict(rsp.desired.composite.resource)["status"]
        assert out == core.status(PARAMS, CREATED)
        assert set(rsp.desired.resources) == {core.NETWORK, core.SUBNETWORK}

    @pytest.mark.parametrize(
        "parameters",
        [
            {**PARAMS, "externalNames": {"network": ""}},
            {"id": ID},
        ],
        ids=["empty-external-name", "missing-region"],
    )
    def test_spec_the_xrd_rejects_is_fatal(self, parameters):
        rsp = run({**XR, "spec": {"parameters": parameters}})
        assert rsp.results[0].severity == fnv1.SEVERITY_FATAL
        assert "invalid Network" in rsp.results[0].message
        assert not rsp.desired.resources

    def test_validation_errors_are_fatal_and_compose_nothing(self):
        rsp = run({**XR, "spec": {"parameters": {**PARAMS, "id": "Bad_ID"}}})
        assert rsp.results[0].severity == fnv1.SEVERITY_FATAL
        assert "Bad_ID" in rsp.results[0].message
        assert not rsp.desired.resources
        assert not rsp.desired.composite.resource.fields
