# Composition Function

Composes a Network's VPC network and subnetwork, and publishes the status other
domains consume.

- `function/core.py`: builds the composed resources and the XR status, and
  validates the parameters. No Crossplane SDK, so it's directly unit-testable.
- `function/fn.py`: the gRPC adapter that calls `core` and writes the response.
- `function/serialize.py`: turns models into what the SDK accepts.

## Unit tests

They cover what the composition tests in `tests/` can't, such as fields being
absent before the network exists. Generate the models with `up project build`,
then, from this directory, in a virtualenv with `pytest`,
`crossplane-function-sdk-python` and `pydantic`:

```shell
python -m pytest tests -q
```
