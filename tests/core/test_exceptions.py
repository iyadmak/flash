from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from flash.core.exceptions import register_exception_handlers, ItemNotFound


def build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-error")
    async def raise_app_error() -> None:
        raise ItemNotFound

    @app.get("/validation-error")
    async def raise_validation_error(count: int) -> dict[str, int]:
        return {"count": count}

    @app.get("/unexpected-error")
    async def raise_unexpected_error() -> None:
        raise ValueError("error")

    return app


class TestAppErrorHandler:
    async def test_returns_status_code_and_json_shape(self) -> None:
        app = build_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/app-error")
            assert resp.status_code == 404
            assert resp.json() == {
                "error": "item_not_found",
                "detail": "The requested item does not exist.",
            }


class TestValidationHandler:
    async def test_missing_query_params_returns_422_shape(self) -> None:
        app = build_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/validation-error")
            assert resp.status_code == 422
            body = resp.json()
            assert body["error"] == "validation_error"
            assert isinstance(body["detail"], list)
            assert body["detail"][0]["loc"] == ["query", "count"]


class TestUnexpectedErrorHandler:
    async def test_hides_internal_details_behind_generic_500(self) -> None:
        app = build_app()
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/unexpected-error")

        assert resp.status_code == 500
        assert resp.json() == {
            "error": "internal_error",
            "detail": "An unexpected error occurred.",
        }
