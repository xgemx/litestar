Plugins
=======

Litestar supports a plugin system that allows you to extend the functionality of the framework.

.. seealso::

    :doc:`/usage/contrib/sqlalchemy/plugins/index`

Plugins are defined by protocols, and any type that satisfies a protocol can be included in the ``plugins`` argument of
the :class:`app <litestar.app.Litestar>`.

The following plugin protocols are defined.

1. :class:`InitPluginProtocol <litestar.plugins.InitPluginProtocol>`: This protocol defines a contract for plugins
that can interact with the data that is used to instantiate the application instance.

2. :class:`SerializationPluginProtocol <litestar.plugins.SerializationPluginProtocol>`: This protocol defines
the contract for plugins that extend serialization functionality of the application.

InitPluginProtocol
~~~~~~~~~~~~~~~~~~

``InitPluginProtocol`` defines an interface that allows for customization of the application's initialization process.
Init plugins can define dependencies, add route handlers, configure middleware, and much more!

Implementations of these plugins must define a single method:

:meth:`on_app_init(self, app_config: AppConfig) -> AppConfig: <litestar.plugins.InitPluginProtocol.on_app_init>`
----------------------------------------------------------------------------------------------------------------

The method accepts and must return an :class:`AppConfig <litestar.config.app.AppConfig>` instance, which can be modified
and is later used to instantiate the application.

This method is invoked after any ``on_app_init`` hooks have been called, and each plugin is invoked in the order that
they are provided in the ``plugins`` argument of the :class:`app <litestar.app.Litestar>`. Because of this, plugin
authors should make it clear in their documentation if their plugin should be invoked before or after other plugins.

Example
-------

The following example shows a simple plugin that adds a route handler, and a dependency to the application.

.. literalinclude:: /examples/plugins/init_plugin_protocol.py
   :language: python
   :caption: ``InitPluginProtocol`` implementation example

The ``MyPlugin`` class is an implementation of the :class:`InitPluginProtocol <litestar.plugins.InitPluginProtocol>`. It
defines a single method, ``on_app_init()``, which takes an :class:`AppConfig <litestar.config.app.AppConfig>` instance
as an argument and returns same.

In the ``on_app_init()`` method, the dependency mapping is updated to include a new dependency named ``"name"``, which
is provided by the ``get_name()`` function, and ``route_handlers`` is updated to include the ``route_handler()``
function. The modified :class:`AppConfig <litestar.config.app.AppConfig>` instance is then returned.

SerializationPluginProtocol
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SerializationPluginProtocol defines a contract for plugins that provide serialization functionality for data types
that are otherwise unsupported by the framework.

Implementations of these plugins must define the following methods.

:meth:`supports_type(self, parsed_type: ParsedType) -> bool: <litestar.plugins.SerializationPluginProtocol>`
------------------------------------------------------------------------------------------------------------

The method takes a :class:`ParsedType <litestar.typing.ParsedType>` instance as an argument and returns a :class:`bool`
indicating whether the plugin supports serialization for that type.

:meth:`create_dto_for_type(self, parsed_type: ParsedType) -> type[DTOInterface]: <litestar.plugins.SerializationPluginProtocol.create_dto_for_type>`
----------------------------------------------------------------------------------------------------------------------------------------------------

This method accepts a :class:`ParsedType <litestar.typing.ParsedType>` instance as an argument and must return a
:class:`DTOInterface <litestar.dto.interface.DTOInterface>` implementation that can be used to serialize and deserialize
the type.

During application startup, if a data or return annotation is encountered that is not a supported type, is supported by
the plugin, and doesn't otherwise have a ``dto`` or ``return_dto`` defined, the plugin is used to create a DTO type for
that annotation.

Example
-------

The following example shows the actual implementation of the ``SerializationPluginProtocol`` for
`SQLAlchemy <https://www.sqlalchemy.org/>`_ models that is is provided in ``litestar.contrib.sqlalchemy``.

.. literalinclude:: ../../litestar/contrib/sqlalchemy/plugins/serialization.py
   :language: python
   :caption: ``SerializationPluginProtocol`` implementation example

:meth:`supports_type(self, parsed_type: ParsedType) -> bool: <litestar.contrib.sqlalchemy.plugins.SQLAlchemySerializationPlugin.supports_type>`
returns a :class:`bool` indicating whether the plugin supports serialization for the given type. Specifically, we return
``True`` if the parsed type is either a collection of SQLAlchemy models or a single SQLAlchemy model.

:meth:`create_dto_for_type(self, parsed_type: ParsedType) -> type[DTOInterface]: <litestar.contrib.sqlalchemy.plugins.SQLAlchemySerializationPlugin.create_dto_for_type>`
takes a :class:`ParsedType <litestar.typing.ParsedType>` instance as an argument and returns a
:class:`SQLAlchemyDTO <litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO>` subclass and includes some logic that may be
interesting to potential serialization plugin authors.

The first thing the method does is check if the parsed type is a collection of SQLAlchemy models or a single SQLAlchemy
model, retrieves the model type in either case and assigns it to the ``annotation`` variable.

The method then checks if ``annotation`` is already in the ``_type_dto_map`` dictionary. If it is, it returns the
corresponding DTO type. This is done to ensure that multiple :class:`SQLAlchemyDTO <litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO>`
subtypes are not created for the same model.

If the annotation is not in the ``_type_dto_map`` dictionary, the method creates a new DTO type for the annotation,
adds it to the ``_type_dto_map`` dictionary, and returns it.
