import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routers.months import router as months_api_router
from api.handlers import router

app = FastAPI(title="months")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)
app.include_router(months_api_router)


if __name__ == "__main__":
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)
