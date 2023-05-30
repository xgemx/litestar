from typing import List

import pytest

from litestar import Controller, Router, get
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client


def test_layered_parameters_injected_correctly() -> None:
    class MyController(Controller):
        path = "/controller"
        parameters = {"controller1": Parameter(lt=100), "controller2": Parameter(str, query="controller3")}

        @get("/{local:int}")
        def my_handler(
            self,
            local: float,
            controller1: int,
            controller2: str,
            router1: str,
            router2: float,
            app1: str,
            app2: List[str],
        ) -> dict:
            assert isinstance(local, float)
            assert isinstance(controller1, int)
            assert isinstance(controller2, str)
            assert isinstance(router1, str)
            assert isinstance(router2, float)
            assert isinstance(app1, str)
            assert isinstance(app2, list)
            return {"message": "ok"}

    router = Router(
        path="/router",
        route_handlers=[MyController],
        parameters={
            "router1": Parameter(str, pattern="^[a-zA-Z]$"),
            "router2": Parameter(float, multiple_of=5.0, header="router3"),
        },
    )

    with create_test_client(
        route_handlers=router,
        parameters={
            "app1": Parameter(str, cookie="app4"),
            "app2": Parameter(List[str], min_items=2),
            "app3": Parameter(bool, required=False),
        },
    ) as client:
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"app4": "jeronimo"}  # type: ignore

        query = {"controller1": "99", "controller3": "tuna", "router1": "albatross", "app2": ["x", "y"]}
        headers = {"router3": "10"}

        response = client.get("/router/controller/1", params=query, headers=headers)
        assert response.json() == {"message": "ok"}
        assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize("parameter", ["controller1", "controller3", "router1", "router3", "app4", "app2"])
def test_layered_parameters_validation(parameter: str) -> None:
    class MyController(Controller):
        path = "/controller"
        parameters = {"controller1": Parameter(int, lt=100), "controller2": Parameter(str, query="controller3")}

        @get("/{local:int}")
        def my_handler(self) -> dict:
            return {}

    router = Router(
        path="/router",
        route_handlers=[MyController],
        parameters={
            "router1": Parameter(str, pattern="^[a-zA-Z]$"),
            "router2": Parameter(float, multiple_of=5.0, header="router3"),
        },
    )

    with create_test_client(
        route_handlers=router,
        parameters={
            "app1": Parameter(str, cookie="app4"),
            "app2": Parameter(List[str], min_items=2),
            "app3": Parameter(bool, required=False),
        },
    ) as client:
        query = {"controller1": "99", "controller3": "tuna", "router1": "albatross", "app2": ["x", "y"]}
        headers = {"router3": "10"}
        cookies = {"app4": "jeronimo"}

        if parameter in headers:
            headers = {}
        elif parameter in cookies:
            cookies = {}
        else:
            query.pop(parameter)

        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = cookies  # type: ignore

        response = client.get("/router/controller/1", params=query, headers=headers)

        assert response.status_code == HTTP_400_BAD_REQUEST
        assert f"Missing required parameter {parameter}" in response.json()["detail"]


def test_layered_parameters_defaults_and_overrides() -> None:
    class MyController(Controller):
        path = "/controller"
        parameters = {"controller1": Parameter(int, default=50), "controller2": Parameter(str, query="controller3")}

        @get("/{local:int}")
        def my_handler(
            self,
            local: float,
            controller1: int,
            controller2: str = Parameter(str, query="controller4"),
            app1: str = Parameter(default="moishe"),
        ) -> dict:
            assert app1 == "moishe"
            assert controller2 == "jeronimo"
            assert controller1 == 50
            return {"message": "ok"}

    router = Router(
        path="/router",
        route_handlers=[MyController],
    )

    with create_test_client(
        route_handlers=router,
        parameters={
            "app1": Parameter(str, default="haim"),
        },
    ) as client:
        query = {"controller4": "jeronimo"}

        response = client.get("/router/controller/1", params=query)
        assert response.json() == {"message": "ok"}
        assert response.status_code == HTTP_200_OK
