from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar.dto.factory.types import FieldDefinition

if TYPE_CHECKING:
    from typing import Any

    from typing_extensions import Self, TypeAlias

    from litestar.typing import ParsedType


@dataclass(frozen=True)
class NestedFieldInfo:
    """Type for representing fields and model type of nested model type."""

    __slots__ = ("model", "field_definitions")

    model: type[Any]
    field_definitions: FieldDefinitionsType


@dataclass(frozen=True)
class TransferType:
    """Type for representing model types for data transfer."""

    __slots__ = ("parsed_type",)

    parsed_type: ParsedType


@dataclass(frozen=True)
class SimpleType(TransferType):
    """Represents indivisible, non-composite types."""

    __slots__ = ("nested_field_info",)

    nested_field_info: NestedFieldInfo | None
    """If the type is a 'nested' type, this is the model generated for transfer to/from it."""


@dataclass(frozen=True)
class CompositeType(TransferType):
    """A type that is made up of other types."""

    __slots__ = ("has_nested",)

    has_nested: bool
    """Whether the type represents nested model types within itself."""


@dataclass(frozen=True)
class UnionType(CompositeType):
    """Type for representing union types for data transfer."""

    __slots__ = ("inner_types",)

    inner_types: tuple[CompositeType | SimpleType, ...]


@dataclass(frozen=True)
class CollectionType(CompositeType):
    """Type for representing collection types for data transfer."""

    __slots__ = ("inner_type",)

    inner_type: CompositeType | SimpleType


@dataclass(frozen=True)
class TupleType(CompositeType):
    """Type for representing tuples for data transfer."""

    __slots__ = ("inner_types",)

    inner_types: tuple[CompositeType | SimpleType, ...]


@dataclass(frozen=True)
class MappingType(CompositeType):
    """Type for representing mappings for data transfer."""

    __slots__ = ("key_type", "value_type")

    key_type: CompositeType | SimpleType
    value_type: CompositeType | SimpleType


@dataclass(frozen=True)
class TransferFieldDefinition(FieldDefinition):
    __slots__ = (
        "is_excluded",
        "is_partial",
        "serialization_name",
        "transfer_type",
    )

    transfer_type: TransferType
    """Type of the field for transfer."""
    serialization_name: str
    """Name of the field as it should feature on the transfer model."""
    is_partial: bool
    """Whether the field is optional for transfer."""
    is_excluded: bool
    """Whether the field should be excluded from transfer."""

    @classmethod
    def from_field_definition(
        cls,
        field_definition: FieldDefinition,
        transfer_type: TransferType,
        serialization_name: str,
        is_partial: bool,
        is_excluded: bool,
    ) -> Self:
        return cls(
            name=field_definition.name,
            default=field_definition.default,
            parsed_type=field_definition.parsed_type,
            default_factory=field_definition.default_factory,
            serialization_name=serialization_name,
            unique_model_name=field_definition.unique_model_name,
            transfer_type=transfer_type,
            dto_field=field_definition.dto_field,
            is_partial=is_partial,
            is_excluded=is_excluded,
        )


FieldDefinitionsType: TypeAlias = "tuple[TransferFieldDefinition, ...]"
"""Generic representation of names and types."""
