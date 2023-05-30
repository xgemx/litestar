SQLAlchemy Models & Repository
==============================

Litestar comes with a built-in repository class
(:class:`SQLAlchemyAsyncRepository <litestar.contrib.sqlalchemy.repository.SQLAlchemyAsyncRepository>`)
for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ to make CRUD operations easier.

Features
--------

* Pre-configured ``DeclarativeBase`` for :doc:`SQLAlchemy <sqlalchemy:index>` 2.0 that includes a
  UUID or Big Integer based primary-key,
  a  `sentinel column <https://docs.sqlalchemy.org/en/20/core/connections.html#configuring-sentinel-columns/>`_ and
  an optional version with audit columns.
* Generic synchronous and asynchronous repositories for select, insert, update, and delete operations on SQLAlchemy models
* Implements optimized methods for bulk inserts, updates, and deletes.
* Integrated counts, pagination, sorting, filtering with ``LIKE``, ``IN``, and dates before and/or after.
* Support for SQLite via `aiosqlite <https://aiosqlite.omnilib.dev/en/stable/>`_ or `sqlite <https://docs.python.org/3/library/sqlite3.html>`_, Postgres
  via `asyncpg <https://magicstack.github.io/asyncpg/current/>`_ or `psycopg3 (async or sync) <https://www.psycopg.org/psycopg3/>`_, MySQL via
  `asyncmy <https://github.com/long2ice/asyncmy>`_, and Oracle via `oracledb <https://oracle.github.io/python-oracledb/>`_.

Basic Use
---------

To use the :class:`SQLAlchemyAsyncRepository <litestar.contrib.sqlalchemy.repository.SQLAlchemyAsyncRepository>`
repository, you must first define your models using one of the included built-in ``DeclarativeBase`` ORM base
implementations:

* :class:`UUIDBase <litestar.contrib.sqlalchemy.base.UUIDBase>`
* :class:`UUIDAuditBase <litestar.contrib.sqlalchemy.base.UUIDAuditBase>`

Both include a ``UUID`` based primary key
and ``UUIDAuditBase`` includes an ``updated`` and ``created`` timestamp column.

* :class:`BigIntBase <litestar.contrib.sqlalchemy.base.BigIntBase>`
* :class:`BigIntAuditBase <litestar.contrib.sqlalchemy.base.BigIntAuditBase>`

Both include a ``BigInteger`` based primary key
and ``BigIntAuditBase`` includes an ``updated`` and ``created`` timestamp column.

Models using these bases also include the following enhancements:
* Auto-generated snake-case table name from class name
* Pydantic BaseModel and Dict classes map to an optimized JSON type that is
:class:`JSONB <sqlalchemy.dialects.postgresql.JSONB>` for the Postgres and
:class:`JSON <sqlalchemy.types.JSON>` for other dialects.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_declarative_models.py
    :caption: sqlalchemy_declarative_models.py
    :language: python

Basic Controller Integration
-----------------------------

Once you have declared your models, you are ready to use the ``SQLAlchemyAsyncRepository`` class with
your controllers and function based routes.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :caption: sqlalchemy_async_repository.py
    :language: python

Alternately, you may use the ``SQLAlchemyAsyncRepository`` class for your synchronous database connection.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_sync_repository.py
    :caption: sqlalchemy_sync_repository.py
    :language: python
