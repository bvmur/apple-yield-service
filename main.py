from fastapi import FastAPI
import uvicorn  
from api.handlers import router
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="draft-apple")

# @app.get("/")
# def read_root():
#     return {"message": "Hello, World!"}

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)