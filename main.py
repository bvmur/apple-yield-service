import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routers.months import router as months_api_router
from api.routers.users import router as users_api_router
from api.handlers import router

tags_metadata = [
    {"name": "months", "description": "Месяцы сезона (услуги): список, лента, черновик, публикация, удаление, лайки"},
    {"name": "users", "description": "Регистрация, вход и выход"},
]

app = FastAPI(
    title="Урожайность сада яблонь",
    description="Без входа доступно только чтение (список и лента)."
                "Методы создателя после входа: сессия хранится в Redis, клиент получает куку session_id.",
    version="1.0",
    openapi_tags=tags_metadata,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router, include_in_schema=False)  # страницы ЛР2 — не API, в Swagger не показываем
app.include_router(months_api_router)
app.include_router(users_api_router)



if __name__ == "__main__":
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)

