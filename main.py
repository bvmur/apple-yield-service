from fastapi import FastAPI
import uvicorn  
from api.handlers import router
from api.months_api import router as months_api_router
from api.users_api import router as users_api_router
from core.errors import register_error_handlers
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="draft-apple")

# @app.get("/")
# def read_root():
#     return {"message": "Hello, World!"}

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router, include_in_schema=False)  # SSR-страницы (ЛР2), в /docs не показываем
app.include_router(months_api_router)    # REST API месяцев (ЛР3)
app.include_router(users_api_router)     # REST API пользователей (ЛР3)
register_error_handlers(app)             # ошибки в формате {"status": "fail", "message": ...}

if __name__ == "__main__":
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)