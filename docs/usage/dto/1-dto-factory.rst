DTO Factory
===========

Litestar maintains a suite of DTO factory types that can be used to create DTOs for use with popular data modelling
libraries, such as ORMs. These take a model type as a generic type argument, and create subtypes of
:class:`AbstractDTOFactory <litestar.dto.factory.abc.AbstractDTOFactory>` that support conversion of that model type to
and from raw bytes.

The following factories are currently available:

- :class:`DataclassDTO <litestar.dto.factory.stdlib.DataclassDTO>`
- :class:`MsgspecDTO <litestar.contrib.msgspec.MsgspecDTO>`
- :class:`PydanticDTO <litestar.contrib.pydantic.PydanticDTO>`
- :class:`SQLAlchemyDTO <litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO>`

Using DTO Factories
-------------------

DTO factories are used to create DTOs for use with a particular data modelling library. The following example creates
a DTO for use with a SQLAlchemy model:

.. literalinclude:: /examples/data_transfer_objects/factory/simple_dto_factory_example.py
    :caption: A SQLAlchemy model DTO
    :language: python

Here we see that a SQLAlchemy model is used as both the ``data`` and return annotation for the handler, and while
Litestar does not natively support encoding/decoding to/from SQLAlchemy models, through
:class:`SQLAlchemyDTO <litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO>` we can do this.

However, we do have some issues with the above example. Firstly, the user's password has been returned to them in the
response from the handler. Secondly, the user is able to set the ``created_at`` field on the model, which should only
ever be set once, and defined internally.

Let's explore how we can configure DTOs to manage scenarios like these.

.. _dto-marking-fields:

Marking fields
--------------

The :func:`dto_field <litestar.dto.factory.dto_field>` function can be used to mark model attributes with DTO-based
configuration.

Fields marked as ``"private"`` or ``"read-only"`` will not be parsed from client data into the user model, and
``"private"`` fields are never serialized into return data.

.. literalinclude:: /examples/data_transfer_objects/factory/marking_fields.py
    :caption: Marking fields
    :language: python
    :emphasize-lines: 6,14,15
    :linenos:

.. note:

    The procedure for "marking" a model field will vary depending on the library. For example,
    :class:`DataclassDTO <.dto.factory.stdlib.dataclass.DataclassDTO>` expects that the mark is made in the ``metadata``
    parameter to ``dataclasses.field``.

Excluding fields
----------------

Fields can be explicitly excluded using :class:`DTOConfig <litestar.dto.factory.DTOConfig>`.

The following example demonstrates excluding attributes from the serialized response, including excluding fields from
nested models.

.. literalinclude:: /examples/data_transfer_objects/factory/excluding_fields.py
    :caption: Excluding fields
    :language: python
    :emphasize-lines: 6,10,31,32,35
    :linenos:

Examining the output of the above POST request, we can see that the user's ID, the ID of the user's address field, and
the user's street address are excluded from the serialized response.

Renaming fields
---------------

Fields can be renamed using :class:`DTOConfig <litestar.dto.factory.DTOConfig>`. The following example uses the name
``userName`` client-side, and ``user`` internally.

.. literalinclude:: /examples/data_transfer_objects/factory/renaming_fields.py
    :caption: Renaming fields
    :language: python
    :emphasize-lines: 4,8,19,20,24
    :linenos:

Fields can also be renamed using a renaming strategy that will be applied to all fields. The following example uses a pre-defined rename strategy that will convert all field names to camel case on client-side.

.. literalinclude:: /examples/data_transfer_objects/factory/renaming_all_fields.py
    :caption: Renaming fields
    :language: python
    :emphasize-lines: 4,8,19,20,21,22,24
    :linenos:

Fields that are directly renamed using `rename_fields` mapping will be excluded from `rename_strategy`.

The rename strategy either accepts one of the pre-defined strategies: "camel", "pascal", "upper", "lower", or it can be provided a callback that accepts the field name as an argument and should return a string.

Type checking
-------------

Factories check that the types to which they are assigned are a subclass of the type provided as the generic type to the
DTO factory. This means that if you have a handler that accepts a ``User`` model, and you assign a ``UserDTO`` factory
to it, the DTO will only accept ``User`` types for "data" and return types.

.. literalinclude:: /examples/data_transfer_objects/factory/type_checking.py
    :caption: Type checking
    :language: python
    :emphasize-lines: 25,26,31
    :linenos:

In the above example, the handler is declared to use ``UserDTO`` which has been type-narrowed with the ``User`` type.
However, we annotate the handler with the ``Foo`` type. This will raise an error such as this at runtime:

    litestar.dto.factory.exc.InvalidAnnotation: DTO narrowed with
    '<class 'docs.examples.data_transfer_objects.factory.type_checking.User'>', handler type is
    '<class 'docs.examples.data_transfer_objects.factory.type_checking.Foo'>'

Nested fields
-------------

The depth of related items parsed from client data and serialized into return data can be controlled using the
``max_nested_depth`` parameter to :class:`DTOConfig <litestar.dto.factory.DTOConfig>`.

In this example, we set ``max_nested_depth=0`` for the DTO that handles inbound client data, and leave it at the default
of ``1`` for the return DTO.

.. literalinclude:: /examples/data_transfer_objects/factory/related_items.py
    :caption: Type checking
    :language: python
    :emphasize-lines: 25,35,39
    :linenos:

When the handler receives the client data, we can see that the ``b`` field has not been parsed into the ``A`` model that
is injected for our data parameter (line 35).

We then add a ``B`` instance to the data (line 39), which includes a reference back to ``a``, and from inspection of the
return data can see that ``b`` is included in the response data, however ``b.a`` is not, due to the default
``max_nested_depth`` of ``1``.

DTO Data
--------

Sometimes we need to be able to access the data that has been parsed and validated by the DTO, but not converted into
an instance of our data model.

In the following example, we create a ``Person`` model, that is a :func:`dataclass <dataclasses.dataclass>` with 3
required fields, ``id``, ``name``, and ``age``.

We also create a DTO that doesn't allow clients to set the ``id`` field on the ``Person`` model and set it on the
handler.

.. literalinclude:: /examples/data_transfer_objects/factory/dto_data_problem_statement.py
    :language: python
    :emphasize-lines: 18,19,20,21,27
    :linenos:

Notice that we get a ``500`` response from the handler - this is because the DTO has attempted to convert the request
data into a ``Person`` object and failed because it has no value for the required ``id`` field.

One way to handle this is to create different models, e.g., we might create a ``CreatePerson`` model that has no ``id``
field, and decode the client data into that. However, this method can become quite cumbersome when we have a lot of
variability in the data that we accept from clients, for example,
`PATCH <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH>`_ requests.

This is where the :class:`DTOData <litestar.dto.factory.DTOData>` class comes in. It is a generic class that accepts the
type of the data that it will contain, and provides useful methods for interacting with that data.

.. literalinclude:: /examples/data_transfer_objects/factory/dto_data_usage.py
    :language: python
    :emphasize-lines: 7,25,27
    :linenos:

In the above example, we've injected an instance of :class:`DTOData <litestar.dto.factory.DTOData>` into our handler,
and have used that to create our ``Person`` instance, after augmenting the client data with a server generated ``id``
value.

Consult the :class:`Reference Docs <litestar.dto.factory.DTOData>` for more information on the methods available.

.. _dto-create-instance-nested-data:

Providing values for nested data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To augment data used to instantiate our model instances, we can provide keyword arguments to the
:meth:`create_instance() <litestar.dto.factory.DTOData.create_instance>` method.

Sometimes we need to provide values for nested data, for example, when creating a new instance of a model that has a
nested model with excluded fields.

.. literalinclude:: /examples/data_transfer_objects/factory/providing_values_for_nested_data.py
    :language: python
    :emphasize-lines: 10,11,12,13,21,29,35
    :linenos:

The double-underscore syntax ``address__id`` passed as a keyword argument to the
:meth:`create_instance() <litestar.dto.factory.DTOData.create_instance>` method call is used to specify a value for a
nested attribute. In this case, it's used to provide a value for the ``id`` attribute of the ``Address`` instance nested
within the ``Person`` instance.

This is a common convention in Python for dealing with nested structures. The double underscore can be interpreted as
"traverse through", so ``address__id`` means "traverse through address to get to id".

In the context of this script, ``create_instance(id=1, address__id=2)`` is saying "create a new ``Person`` instance from
the client data given an id of ``1``, and supplement the client address data with an id of ``2``".

DTO Factory and PATCH requests
------------------------------

`PATCH <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH>`_ requests are a special case when it comes to
data transfer objects. The reason for this is that we need to be able to accept and validate any subset of the model
attributes in the client payload, which requires some special handling internally.

.. literalinclude:: /examples/data_transfer_objects/factory/patch_requests.py
    :language: python
    :emphasize-lines: 7,21,32,34
    :linenos:

The ``PatchDTO`` class is defined for the Person class. The ``config`` attribute of ``PatchDTO`` is set to exclude the
id field, preventing clients from setting it when updating a person, and the ``partial`` attribute is set to ``True``,
which allows the DTO to accept a subset of the model attributes.

Inside the handler, the :meth:`DTOData.update_instance <litestar.dto.factory.DTOData.update_instance>` method is called
to update the instance of ``Person`` before returning it.

In our request, we set only the ``name`` property of the ``Person``, from ``"Peter"`` to ``"Peter Pan"`` and received
the full object - with the modified name - back in the response.

Implicit Private Fields
-----------------------

Fields that are named with a leading underscore are considered "private" by default. This means that they will not be
parsed from client data, and will not be serialized into return data.

.. literalinclude:: /examples/data_transfer_objects/factory/leading_underscore_private.py
    :language: python
    :linenos:

This can be overridden by setting the
:attr:`DTOConfig.leading_underscore_private <litestar.dto.factory.DTOConfig.underscore_fields_private>` attribute to
``False``.

.. literalinclude:: /examples/data_transfer_objects/factory/leading_underscore_private_override.py
    :language: python
    :linenos:
    :emphasize-lines: 14,15
