from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from data.collections import months_db

router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/")
def get_catalog(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"months": months_db}
        )

@router.get("/month/{month_id}")
def get_month_detail(request: Request, month_id: int):
    month = next((m for m in months_db if m["id"] == month_id), None)
    
    return templates.TemplateResponse(
        request=request,
        name="month.html",
        context={"month": month}
    )
    


# @router.get("/hotel/{hotel_id}")
# def get_hotel_detail(request: Request, hotel_id: int):
#     hotel = next((h for h in hotels_db if h["id"] == hotel_id), None)
    
#     return templates.TemplateResponse(
#         request=request,
#         name="hotel.html", 
#         context={"hotel": hotel}
#     )

# from fastapi import APIRouter, Request
# from fastapi.templating import Jinja2Templates
# from data.collections import hotels_db

# router = APIRouter()
# templates = Jinja2Templates(directory="templates")

# @router.get("/")
# def get_catalog(request: Request):
#     # Добавляем context явно
#     return templates.TemplateResponse(
#         request=request,
#         name="index.html", 
#         context={"hotels": hotels_db}
#     )
