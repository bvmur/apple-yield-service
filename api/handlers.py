from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from data.collections import months_db

router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/")
def get_months_catalog(request: Request, temp_from: str = ""):
    
    temp = None
    if temp_from != "":
        try:
            temp = int(temp_from)
        except ValueError:
            temp = None
            
    
    months = [
        {**month, "likes_count": len(month["likes"])}
        for month in months_db
        if month["status"] == "published" and (temp is None or month["norm_temp"] >= temp)
        ]
            
    return templates.TemplateResponse(
        request=request,
        name="month_ctlg.html",
        context={"months": months, "temp": temp}
        )

@router.get("/month")
@router.get("/month/{month_id}")
def get_month_feed(request: Request, month_id: int | None = None, next_month: bool = Query(default=False, alias="next")):
    
    published = [month for month in months_db if month["status"] == "published"]
    
    index: int | None
    if month_id is None:
        index = 0
    else:
        index = next((i for i, m in enumerate(published) if m["id"] == month_id), None)
        if index is None:
            raise HTTPException(status_code=404, detail="Месяц не найден.")
    
    if next_month:
        index = (index + 1) % len(published)
    month = published[index]
    month = {**month, "likes_count": len(month["likes"])}

    return templates.TemplateResponse(
        request=request,
        name="month_feed.html",
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
