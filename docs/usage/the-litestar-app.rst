The Litestar App
================


Application object
------------------

At the root of every Litestar application is an instance of the :class:`Litestar <litestar.app.Litestar>`
class. Typically, this code will be placed in a file called ``main.py`` at the project's root directory.

Creating an app is straightforward – the only required arg is a list
of :class:`Controllers <.controller.Controller>`, :class:`Routers <.router.Router>`
or :class:`Route handlers <.handlers.BaseRouteHandler>`:

.. literalinclude:: /examples/hello_world.py
    :caption: Hello World
    :language: python


The app instance is the root level of the app - it has the base path of ``/`` and all root level Controllers, Routers
and Route Handlers should be registered on it.

.. seealso::

    To learn more about registering routes, check out this chapter in the documentation:
    :ref:`usage/routing:Registering Routes`


Validation Backends
-------------------

Litestar supports both `attrs <https://www.attrs.org/en/stable/>`_ and `pydantic <https://docs.pydantic.dev/>`_ as
validation backends. If you have one of these libraries installed alongside Litestar, it will be used automatically.
If you have both of these installed though, Litestar will default to using attrs unless a handler uses a pydantic-specific
type or a custom class that has the pydantic ``__get_validators__`` dunder defined. You can change this behaviour by
setting the ``preferred_validation_backend`` kwarg to ``pydantic``:


.. code-block:: python

   from litestar import Litestar

   app = Litestar(route_handlers=..., preferred_validation_backend="pydantic")


Startup and Shutdown
--------------------

You can pass a list of callables - either sync or async functions, methods or class instances - to the ``on_startup``
/ ``on_shutdown`` kwargs of the :class:`Litestar <litestar.app.Litestar>` instance. Those will be called in
order, once the ASGI server (uvicorn, hypercorn etc.) emits the respective event.

.. mermaid::

   flowchart LR
       Startup[ASGI-Event: lifespan.startup] --> before_startup --> on_startup --> after_startup
       Shutdown[ASGI-Event: lifespan.shutdown] --> before_shutdown --> on_shutdown --> after_shutdown

A classic use case for this is database connectivity. Often, we want to establish a database connection on application
startup, and then close it gracefully upon shutdown.

For example, lets create a database connection using the async engine from
`SQLAlchemy <https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html>`_. We create two functions, one to get or
establish the connection, and another to close it, and then pass them to the Litestar constructor:

.. literalinclude:: /examples/startup_and_shutdown.py
    :caption: Startup and Shutdown
    :language: python

.. _lifespan-context-managers:

Lifespan context managers
-------------------------

In addition to the lifespan hooks, Litestar also supports managing the lifespan of an
application using asynchronous context managers. This can be useful when dealing with
long running tasks, or those that need to keep a certain context object, such as a
connection, around.


.. literalinclude:: /examples/application_hooks/lifespan_manager.py
    :language: python
    :caption: Handling a database connection

.. _application-state:

Using Application State
-----------------------

As seen in the examples for the `on_startup <#before-after-startup>`_ / `on_shutdown <#before-after-shutdown>`_ ,
callables passed to these hooks can receive an optional kwarg called ``state``, which is the application's state object.
The advantage of using application ``state``, is that it can be accessed during multiple stages of the connection, and
it can be injected into dependencies and route handlers.

The Application State is an instance of the :class:`State <.datastructures.state.State>` datastructure, and it is accessible
via the :class:`app.state <.app.Litestar>` attribute. As such it can be accessed wherever the app instance is accessible.

It's important to understand in this context that the application instance is injected into the ASGI ``scope`` mapping for
each connection (i.e. request or websocket connection) as ``scope["app"].state``. This makes the application accessible
wherever the scope mapping is available, e.g. in middleware, on :class:`Request <.connection.request.Request>` and
:class:`Websocket <.connection.websocket.WebSocket>` instances (accessible as ``request.app`` / ``socket.app``) and many
other places.

Therefore, state offers an easy way to share contextual data between disparate parts of the application, as seen below:

.. literalinclude:: /examples/application_state/using_application_state.py
    :caption: Using Application State
    :language: python

.. _Initializing Application State:

Initializing Application State
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To seed application state, you can pass a :class:`State <.datastructures.state.State>` object to the ``state`` kwarg of
the Litestar constructor:

.. literalinclude:: /examples/application_state/passing_initial_state.py
    :caption: Using Application State
    :language: python


.. note::

    :class:`State <.datastructures.state.State>` can be initialized with a dictionary, an instance of
    :class:`ImmutableState <.datastructures.state.ImmutableState>` or :class:`State <.datastructures.state.State>`,
    or a list of tuples containing key/value pairs.

.. attention::

    You may instruct :class:`State <.datastructures.state.State>` to deep copy initialized data to prevent mutation from
    outside the application context. To do this, pass ``deep_copy=True`` to the :class:`State <.datastructures.state.State>`
    constructor.

Injecting Application State into Route Handlers and Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As seen in the above example, Litestar offers an easy way to inject state into route handlers and dependencies - simply
by specifying ``state`` as a kwarg to the handler function. I.e., you can simply do this in handler function or dependency
to access the application state:

.. code-block:: python

   from litestar import get
   from litestar.datastructures import State


   @get("/")
   def handler(state: State) -> None:
       ...

When using this pattern you can specify the class to use for the state object. This type is not merely for type
checkers, rather Litestar will instantiate a new state instance based on the type you set there. This allows users to
use custom classes for State, e.g.:

While this is very powerful, it might encourage users to follow anti-patterns: it's important to emphasize that using
state can lead to code that's hard to reason about and bugs that are difficult to understand, due to changes in
different ASGI contexts. As such, this pattern should be used only when it is the best choice and in a limited fashion.
To discourage its use, Litestar also offers a builtin ``ImmutableState`` class. You can use this class to type state and
ensure that no mutation of state is allowed:

.. literalinclude:: /examples/application_state/using_immutable_state.py
    :caption: Using Custom State
    :language: python



Static Files
------------

Static files are served by the app from predefined locations. To configure static file serving, either pass an
instance of :class:`StaticFilesConfig <.static_files.config.StaticFilesConfig>` or a list
thereof to :class:`Litestar <.app.Litestar>` using the ``static_files_config`` kwarg.

For example, lets say our Litestar app is going to serve **regular files** from the ``my_app/static`` folder and **html
documents** from the ``my_app/html`` folder, and we would like to serve the **static files** on the ``/files`` path,
and the **html files** on the ``/html`` path:

.. code-block:: python

   from litestar import Litestar
   from litestar.static_files.config import StaticFilesConfig

   app = Litestar(
       route_handlers=[...],
       static_files_config=[
           StaticFilesConfig(directories=["static"], path="/files"),
           StaticFilesConfig(directories=["html"], path="/html", html_mode=True),
       ],
   )

Matching is done based on filename, for example, assume we have a request that is trying to retrieve the path
``/files/file.txt``\ , the **directory for the base path** ``/files`` **will be searched** for the file ``file.txt``. If it is
found, the file will be sent, otherwise a **404 response** will be sent.

If ``html_mode`` is enabled and no specific file is requested, the application will fall back to serving ``index.html``. If
no file is found the application will look for a ``404.html`` file in order to render a response, otherwise a 404
:class:`NotFoundException <.exceptions.http_exceptions.NotFoundException>` will be returned.

You can provide a ``name`` parameter to ``StaticFilesConfig`` to identify the given config and generate links to files in
folders belonging to that config. ``name`` should be a unique string across all static configs and
`route handlers <usage/route-handlers:Route Handler Indexing>`_.

.. code-block:: python

   from litestar import Litestar
   from litestar.static_files.config import StaticFilesConfig

   app = Litestar(
       route_handlers=[...],
       static_files_config=[
           StaticFilesConfig(
               directories=["static"], path="/some_folder/static/path", name="static"
           ),
       ],
   )

   url_path = app.url_for_static_asset("static", "file.pdf")
   # /some_folder/static/path/file.pdf

Sending files as attachments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, files are sent "inline", meaning they will have a ``Content-Disposition: inline`` header.
To send them as attachments, use the ``send_as_attachment=True`` flag, which will add a
``Content-Disposition: attachment`` header:

.. code-block:: python

   from litestar import Litestar
   from litestar.static_files.config import StaticFilesConfig

   app = Litestar(
       route_handlers=[...],
       static_files_config=[
           StaticFilesConfig(
               directories=["static"],
               path="/some_folder/static/path",
               name="static",
               send_as_attachment=True,
           ),
       ],
   )

File System support and Cloud Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`StaticFilesConfig <.static_files.StaticFilesConfig>` class accepts a value called ``file_system``,
which can be any class adhering to the Litestar :class:`FileSystemProtocol <litestar.types.FileSystemProtocol>`.

This protocol is similar to the file systems defined by `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_,
which cover all major cloud providers and a wide range of other use cases (e.g. HTTP based file service, ``ftp`` etc.).

In order to use any file system, simply use `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_ or one of
the libraries based upon it, or provide a custom implementation adhering to the
:class:`FileSystemProtocol <litestar.types.FileSystemProtocol>`.

Logging
-------

Litestar has builtin pydantic based logging configuration that allows users to easily define logging:

.. code-block:: python

   from litestar import Litestar, Request, get
   from litestar.logging import LoggingConfig


   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("inside a request")
       return None


   logging_config = LoggingConfig(
       loggers={
           "my_app": {
               "level": "INFO",
               "handlers": ["queue_listener"],
           }
       }
   )

   app = Litestar(route_handlers=[my_router_handler], logging_config=logging_config)

.. attention::

    Litestar configures a non-blocking `QueueListenerHandler` which
    is keyed as `queue_listener` in the logging configuration. The above example is using this handler,
    which is optimal for async applications. Make sure to use it in your own loggers as in the above example.

Using Picologging
^^^^^^^^^^^^^^^^^

`Picologging <https://github.com/microsoft/picologging>`_ is a high performance logging library that is developed by
Microsoft. Litestar will default to using this library automatically if its installed - requiring zero configuration on
the part of the user. That is, if ``picologging`` is present the previous example will work with it automatically.

Using StructLog
^^^^^^^^^^^^^^^

`StructLog <https://www.structlog.org/en/stable/>`_ is a powerful structured-logging library. Litestar ships with a dedicated
logging config for using it:

.. code-block:: python

   from litestar import Litestar, Request, get
   from litestar.logging import StructLoggingConfig


   @get("/")
   def my_router_handler(request: Request) -> None:
       request.logger.info("inside a request")
       return None


   logging_config = StructLoggingConfig()

   app = Litestar(route_handlers=[my_router_handler], logging_config=logging_config)

Subclass Logging Configs
^^^^^^^^^^^^^^^^^^^^^^^^

You can easily create you own ``LoggingConfig`` class by subclassing
:class:`BaseLoggingConfig <.logging.config.BaseLoggingConfig>` and implementing the ``configure`` method.

Application Hooks
-----------------

Litestar includes several application level hooks that allow users to run their own sync or async callables. While you
are free to use these hooks as you see fit, the design intention behind them is to allow for easy instrumentation for
observability (monitoring, tracing, logging etc.).

.. note::

    All application hook kwargs detailed below receive either a single callable or a list of callables.
    If a list is provided, it is called in the order it is given.


After Exception
^^^^^^^^^^^^^^^

The ``after_exception`` hook takes a :class:`sync or async callable <litestar.types.AfterExceptionHookHandler>` that is called with
three arguments: the ``exception`` that occurred, the ASGI ``scope`` of the request or websocket connection and the
application ``state``.

.. literalinclude:: /examples/application_hooks/after_exception_hook.py
    :caption: After Exception Hook
    :language: python


.. attention::

    This hook is not meant to handle exceptions - it just receives them to allow for side effects.
    To handle exceptions you should define :ref:`exception handlers <usage/exceptions:exception handling>`.

Before Send
^^^^^^^^^^^

The ``before_send`` hook takes a :class:`sync or async callable <litestar.types.BeforeMessageSendHookHandler>` that is called when
an ASGI message is sent. The hook receives the message instance and the application state.

.. literalinclude:: /examples/application_hooks/before_send_hook.py
    :caption: Before Send Hook
    :language: python



Application Init
^^^^^^^^^^^^^^^^

Litestar includes a hook for intercepting the arguments passed to the :class:`Litestar constructor <litestar.app.Litestar>`,
before they are used to instantiate the application.

Handlers can be passed to the ``on_app_init`` parameter on construction of the application, and in turn, each will receive
an instance of :class:`AppConfig <litestar.config.app.AppConfig>` and must return an instance of same.

This hook is useful for applying common configuration between applications, and for use by developers who may wish to
develop third-party application configuration systems.

.. note::

    `on_app_init` handlers cannot be `async def` functions, as they are called within `Litestar.__init__()`, outside of
    an async context.

.. literalinclude:: /examples/application_hooks/on_app_init.py
    :caption: After Exception Hook
    :language: python


.. _layered-architecture:

Layered architecture
--------------------

Litestar has a layered architecture compromising of (generally speaking) 4 layers:


#. The application object
#. Routers
#. Controllers
#. Handlers

There are many parameters that can be defined on every layer, in which case the parameter
defined on the layer **closest to the handler** takes precedence. This allows for maximum
flexibility and simplicity when configuring complex applications and enables transparent
overriding of parameters.

Parameters that support layering are:


* :ref:`after_request <after_request>`
* :ref:`after_response <after_response>`
* :ref:`before_request <before_request>`
* :ref:`cache_control <usage/responses:cache control>`
* :doc:`dependencies </usage/dependency-injection>`
* :doc:`dto </usage/dto/0-basic-use>`
* :ref:`etag <usage/responses:etag>`
* :doc:`exception_handlers </usage/exceptions>`
* :doc:`guards </usage/security/guards>`
* :doc:`middleware </usage/middleware/index>`
* :ref:`opt <handler_opts>`
* :ref:`response_class <usage/responses:custom responses>`
* :ref:`response_cookies <usage/responses:response cookies>`
* :ref:`response_headers <usage/responses:response headers>`
* :doc:`return_dto </usage/dto/0-basic-use>`
* ``security``
* ``tags``
* ``type_encoders``
