"""Turn composed-resource models into what the Crossplane SDK will accept."""


def to_dict(model) -> dict:
    """Serialize a managed-resource model for resource.update().

    resource.update() accepts a model directly, but that path dumps without by_alias, so any
    field whose CRD name is a Python keyword would go out under its Python name and be rejected
    by the API server. Passing a plain dict writes the value through untouched.

    exclude_none emits exactly the fields that were set.
    """
    return model.model_dump(by_alias=True, exclude_none=True, warnings=False)
