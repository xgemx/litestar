from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, Literal

import msgspec
import pytest
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from litestar import Controller, MediaType, get
from litestar._openapi.schema_generation.schema import (
    KWARG_MODEL_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP,
    _process_schema_result,
    create_schema,
    create_schema_for_annotation,
    create_schema_for_dataclass,
    create_schema_for_pydantic_model,
    create_schema_for_typed_dict,
)
from litestar._signature.field import SignatureField
from litestar._signature.models.pydantic_signature_model import PydanticSignatureModel
from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.di import Provide
from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec import ExternalDocumentation, OpenAPIType, Reference
from litestar.openapi.spec.example import Example
from litestar.openapi.spec.schema import Schema
from litestar.params import BodyKwarg, Parameter, ParameterKwarg
from litestar.testing import create_test_client
from tests import Person, Pet

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Callable


def test_process_schema_result() -> None:
    test_str = "abc"
    kwarg_model = ParameterKwarg(
        examples=[Example(value=1)],
        external_docs=ExternalDocumentation(url="https://example.com/docs"),
        content_encoding="utf-8",
        default=test_str,
        title=test_str,
        description=test_str,
        const=True,
        gt=1,
        ge=1,
        lt=1,
        le=1,
        multiple_of=1,
        min_items=1,
        max_items=1,
        min_length=1,
        max_length=1,
        pattern="^[a-z]$",
    )
    schemas: Dict[str, Schema] = {}
    schema = Schema()
    _process_schema_result(
        schema=schema,
        field=SignatureField.create(field_type=str, kwarg_model=kwarg_model),
        generate_examples=False,
        schemas=schemas,
    )
    assert schema.title
    assert schema.const == test_str
    for signature_key, schema_key in KWARG_MODEL_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP.items():
        assert getattr(schema, schema_key) == getattr(kwarg_model, signature_key)


def test_dependency_schema_generation() -> None:
    async def top_dependency(query_param: int) -> int:
        return query_param

    async def mid_level_dependency(header_param: str = Parameter(header="header_param", required=False)) -> int:
        return 5

    async def local_dependency(path_param: int, mid_level: int, top_level: int) -> int:
        return path_param + mid_level + top_level

    class MyController(Controller):
        path = "/test"
        dependencies = {"mid_level": Provide(mid_level_dependency)}

        @get(
            path="/{path_param:int}",
            dependencies={
                "summed": Provide(local_dependency),
            },
            media_type=MediaType.TEXT,
        )
        def test_function(self, summed: int, handler_param: int) -> str:
            return str(summed)

    with create_test_client(
        MyController,
        dependencies={"top_level": Provide(top_dependency)},
        openapi_config=DEFAULT_OPENAPI_CONFIG,
    ) as client:
        handler = client.app.openapi_schema.paths["/test/{path_param}"]
        data = {param.name: {"in": param.param_in, "required": param.required} for param in handler.get.parameters}
        assert data == {
            "path_param": {"in": ParamType.PATH, "required": True},
            "header_param": {"in": ParamType.HEADER, "required": False},
            "query_param": {"in": ParamType.QUERY, "required": True},
            "handler_param": {"in": ParamType.QUERY, "required": True},
        }


def test_get_schema_for_field_type_enum() -> None:
    class Opts(str, Enum):
        opt1 = "opt1"
        opt2 = "opt2"

    class M(BaseModel):
        opt: Opts

    schema = create_schema_for_annotation(
        annotation=PydanticSignatureModel.signature_field_from_model_field(M.__fields__["opt"]).field_type
    )
    assert schema
    assert schema.enum == ["opt1", "opt2"]


def test_handling_of_literals() -> None:
    @dataclass
    class DataclassWithLiteral:
        value: Literal["a", "b", "c"]
        const: Literal[1]

    schemas: Dict[str, Schema] = {}
    result = create_schema(
        field=SignatureField.create(name="", field_type=DataclassWithLiteral),
        generate_examples=False,
        plugins=[],
        schemas=schemas,
    )
    assert isinstance(result, Reference)
    schema = schemas["DataclassWithLiteral"]
    assert isinstance(schema, Schema)
    assert schema.properties
    value = schema.properties["value"]
    assert isinstance(value, Schema)
    assert value.enum == ("a", "b", "c")
    const = schema.properties["const"]
    assert isinstance(const, Schema)
    assert const.const == 1


def test_schema_hashing() -> None:
    schema = Schema(
        one_of=[
            Schema(type=OpenAPIType.STRING),
            Schema(type=OpenAPIType.NUMBER),
            Schema(type=OpenAPIType.OBJECT, properties={"key": Schema(type=OpenAPIType.STRING)}),
        ],
        examples=[Example(value=None), Example(value=[1, 2, 3])],
    )
    assert hash(schema)


def test_title_validation() -> None:
    schemas: Dict[str, Schema] = {}
    create_schema(
        field=SignatureField.create(name="Person", field_type=Person),
        generate_examples=False,
        plugins=[],
        schemas=schemas,
    )
    assert schemas.get("Person")

    create_schema(
        field=SignatureField.create(name="Pet", field_type=Pet),
        generate_examples=False,
        plugins=[],
        schemas=schemas,
    )

    assert schemas.get("Pet")

    with pytest.raises(ImproperlyConfiguredException):
        create_schema(
            field=SignatureField.create(name="Person", field_type=Pet, kwarg_model=BodyKwarg(title="Person")),
            generate_examples=False,
            plugins=[],
            schemas=schemas,
        )


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_create_schema_for_pydantic_model_with_annotated_model_attribute(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]"
) -> None:
    """Test that a model with an annotated attribute is correctly handled."""
    module = create_module(
        f"""
{'from __future__ import annotations' if with_future_annotations else ''}
from typing_extensions import Annotated
from pydantic import BaseModel

class Foo(BaseModel):
    foo: Annotated[int, "Foo description"]
"""
    )
    schema = create_schema_for_pydantic_model(module.Foo, generate_examples=False, plugins=[], schemas={})
    assert schema.properties and "foo" in schema.properties


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_create_schema_for_dataclass_with_annotated_model_attribute(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]"
) -> None:
    """Test that a model with an annotated attribute is correctly handled."""
    module = create_module(
        f"""
{'from __future__ import annotations' if with_future_annotations else ''}
from typing_extensions import Annotated
from dataclasses import dataclass

@dataclass
class Foo:
    foo: Annotated[int, "Foo description"]
"""
    )
    schema = create_schema_for_dataclass(module.Foo, generate_examples=False, plugins=[], schemas={})
    assert schema.properties and "foo" in schema.properties


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_create_schema_for_typedict_with_annotated_required_and_not_required_model_attributes(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]"
) -> None:
    """Test that a model with an annotated attribute is correctly handled."""
    module = create_module(
        f"""
{'from __future__ import annotations' if with_future_annotations else ''}
from typing_extensions import Annotated, Required, NotRequired
from typing import TypedDict

class Foo(TypedDict):
    foo: Annotated[int, "Foo description"]
    bar: Annotated[Required[int], "Bar description"]
    baz: Annotated[NotRequired[int], "Baz description"]
"""
    )
    schema = create_schema_for_typed_dict(module.Foo, generate_examples=False, plugins=[], schemas={})
    assert schema.properties and all(key in schema.properties for key in ("foo", "bar", "baz"))


def test_create_schema_from_msgspec_annotated_type() -> None:
    class Lookup(msgspec.Struct):
        id: Annotated[str, msgspec.Meta(max_length=16, examples=["example"], description="description", title="title")]

    schemas: Dict[str, Schema] = {}
    create_schema(
        field=SignatureField.create(name="Lookup", field_type=Lookup),
        generate_examples=False,
        plugins=[],
        schemas=schemas,
    )
    schema = schemas["Lookup"]
    assert schema.properties["id"].type == OpenAPIType.STRING  # type: ignore
    assert schema.properties["id"].examples == [Example(value="example")]  # type: ignore
    assert schema.properties["id"].description == "description"  # type: ignore
    assert schema.properties["id"].title == "title"  # type: ignore
    assert schema.properties["id"].max_length == 16  # type: ignore


def test_create_schema_for_pydantic_field() -> None:
    class Model(BaseModel):
        value: str = Field(title="title", description="description", example="example", max_length=16)

    schemas: Dict[str, Schema] = {}
    create_schema(
        field=SignatureField.create(name="Model", field_type=Model),
        generate_examples=False,
        plugins=[],
        schemas=schemas,
    )
    schema = schemas["Model"]

    assert schema.properties["value"].description == "description"  # type: ignore
    assert schema.properties["value"].title == "title"  # type: ignore
    assert schema.properties["value"].examples == [Example(value="example")]  # type: ignore
