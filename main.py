import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from auth import create_access_token, authenticate_user, get_current_user, get_password_hash
from database import SessionLocal
from models import User, ChatMonitor
from monitor import init_telegram_client, check_chat_for_user
import json
from urllib.parse import urlencode
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Инициализация Telegram клиента и планировщика
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    await init_telegram_client()
    scheduler.add_job(background_monitoring_job, 'interval', seconds=10, coalesce=True, max_instances=1)
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

# Фоновая задача мониторинга
async def background_monitoring_job():
    db = SessionLocal()
    monitors = db.query(ChatMonitor).all()
    for monitor in monitors:
        try:
            new_last_id = await check_chat_for_user(monitor)
            monitor.last_message_id = new_last_id
            db.commit()
        except Exception as e:
            print(f"Ошибка обновления монитора ID {monitor.id}: {e}")
    db.close()

# === Роуты ===

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

# Регистрация
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    hashed_password = get_password_hash(password)
    user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.close()
    return RedirectResponse(url="/login", status_code=303)

# Авторизация
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = authenticate_user(db, username, password)
    db.close()
    if not user:
        query_params = urlencode({"error": "Неверный логин или пароль"})
        return RedirectResponse(url=f"/login?{query_params}", status_code=303)
    token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return response

# Дашборд
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    db = SessionLocal()

    # Получаем чаты пользователя
    chats = db.query(ChatMonitor).filter(ChatMonitor.user_id == current_user.id).all()

    # Пример данных для статистики (в будущем — из БД)
    stats = {
        "today_leads"      : 24,
        "month_leads"      : 342,
        "conversion_rate"  : "18%",
        "avg_response_time": "12 мин"
    }

    # Пример последних лидов (в будущем — из БД)
    recent_leads = [
        {
            "date"    : "12.04.2023 14:23",
            "name"    : "Мария Иванова",
            "telegram": "@maria_ivanova",
            "source"  : "Чат 'Недвижимость Москвы'",
            "keyword" : "купить квартиру",
            "status"  : "Новый"
        },
        {
            "date"    : "12.04.2023 13:47",
            "name"    : "Сергей Петров",
            "telegram": "@sergey_petrov",
            "source"  : "Канал 'Бизнес консультации'",
            "keyword" : "юридические услуги",
            "status"  : "В работе"
        }
    ]

    db.close()

    return templates.TemplateResponse("dashboard.html", {
        "request"     : request,
        "user"        : {
            "username": current_user.username,
            "email"   : current_user.email,
            "tariff"  : current_user.tariff,
            "role"    : "Менеджер по продажам"  # можно хранить в БД
        },
        "stats"       : stats,
        "recent_leads": recent_leads,
        "chats"       : chats
    })

# Добавить чат
@app.post("/add_chat")
async def add_chat(
    chat_username: str = Form(...),
    keywords: str = Form(...),
    notifications_to: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    chat_count = db.query(ChatMonitor).filter(ChatMonitor.user_id == current_user.id).count()
    if chat_count >= current_user.max_chats:
        return {"error": "Превышен лимит чатов"}

    keyword_list = [kw.strip() for kw in keywords.splitlines() if kw.strip()]
    if len(keyword_list) > current_user.max_keywords_per_chat:
        return {"error": "Превышен лимит ключевых слов"}

    new_chat = ChatMonitor(
        user_id=current_user.id,
        chat_username=chat_username,
        keywords=json.dumps(keyword_list),
        notifications_to=notifications_to
    )
    db.add(new_chat)
    db.commit()
    db.close()
    return f"""
    <div class="chat-card">
        <h3>{chat_username}</h3>
        <p>Ключевые слова: {', '.join(keyword_list)}</p>
        <p>Уведомления: {notifications_to}</p>
        <button hx-delete="/delete_chat/{new_chat.id}" hx-confirm="Удалить?">Удалить</button>
    </div>
    """

# Удалить чат
@app.delete("/delete_chat/{chat_id}")
async def delete_chat(chat_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    chat = db.query(ChatMonitor).filter(ChatMonitor.id == chat_id, ChatMonitor.user_id == current_user.id).first()
    if chat:
        db.delete(chat)
        db.commit()
    db.close()
    return ""

# Смена тарифа
@app.get("/change_tariff", response_class=HTMLResponse)
async def change_tariff(request: Request, current_user: User = Depends(get_current_user)):
    return "Страница смены тарифа — в разработке"

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response

# Точка входа для запуска
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)