import os
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv

load_dotenv()

CATALOG_PATH = Path("data") / "catalog.json"


# ---------- helpers ----------
def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text('{"categories":[]}', encoding="utf-8")
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def save_catalog(catalog: dict) -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


def is_admin(user_id: int) -> bool:
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return False
    admins = {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
    return user_id in admins


def kb_main(user_is_admin: bool):
    kb = InlineKeyboardBuilder()
    kb.button(text="Категории", callback_data="cats")
    kb.button(text="Поиск", callback_data="search:ask")
    kb.adjust(1)
    if user_is_admin:
        kb.button(text="➕ Добавить книгу (админ)", callback_data="admin:add")
        kb.adjust(1)
    return kb.as_markup()


def kb_categories(categories: list[dict]):
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=c["title"], callback_data=f"cat:{c['id']}")
    kb.button(text="⬅️ Назад", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def kb_books(cat_id: str, books: list[dict]):
    kb = InlineKeyboardBuilder()
    for b in books:
        kb.button(text=b["title"], callback_data=f"book:{b['id']}")
    kb.button(text="⬅️ Категории", callback_data="cats")
    kb.adjust(1)
    return kb.as_markup()


def kb_book_actions(book_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Скачать", callback_data=f"dl:{book_id}")
    kb.button(text="⬅️ Назад", callback_data="cats")
    kb.adjust(1)
    return kb.as_markup()


def slugify(s: str) -> str:
    s = s.strip().lower()
    out = []
    prev_dash = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif ch in (" ", "_", ".", ",", "—", "–", ":", ";", "/", "\\"):
            if not prev_dash:
                out.append("-")
                prev_dash = True
    res = "".join(out).strip("-")
    return res if res else "book"


def find_book(catalog: dict, book_id: str) -> dict | None:
    for c in catalog.get("categories", []):
        for b in c.get("books", []):
            if b.get("id") == book_id:
                return b
    return None


def find_category(catalog: dict, cat_id: str) -> dict | None:
    for c in catalog.get("categories", []):
        if c.get("id") == cat_id:
            return c
    return None


def ensure_unique_id(catalog: dict, base_id: str) -> str:
    if not find_book(catalog, base_id):
        return base_id
    n = 2
    while True:
        candidate = f"{base_id}-{n}"
        if not find_book(catalog, candidate):
            return candidate
        n += 1


def search_books(catalog: dict, query: str) -> list[dict]:
    q = query.lower().strip()
    if not q:
        return []
    out = []
    for c in catalog.get("categories", []):
        for b in c.get("books", []):
            title = (b.get("title") or "").lower()
            author = (b.get("author") or "").lower()
            if q in title or q in author:
                out.append({**b, "_category_title": c.get("title", "")})
    return out


# ---------- FSM ----------
class SearchFlow(StatesGroup):
    waiting_query = State()


class AdminAddFlow(StatesGroup):
    waiting_file = State()
    waiting_cat_id = State()
    waiting_cat_title = State()
    waiting_title = State()
    waiting_author = State()
    waiting_description = State()


# ---------- bot ----------
async def main():
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN missing")

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    # /start
    @dp.message(F.text.in_({"/start", "/help"}))
    async def start(m: Message, state: FSMContext):
        await state.clear()
        await m.answer("Ассаляму алейкум.\nВыберите действие:", reply_markup=kb_main(is_admin(m.from_user.id)))

    # home
    @dp.callback_query(F.data == "home")
    async def home(c: CallbackQuery, state: FSMContext):
        await state.clear()
        await c.message.edit_text("Выберите действие:", reply_markup=kb_main(is_admin(c.from_user.id)))
        await c.answer()

    # categories
    @dp.callback_query(F.data == "cats")
    async def cats(c: CallbackQuery):
        catalog = load_catalog()
        cats_list = catalog.get("categories", [])
        if not cats_list:
            await c.message.edit_text("Пока нет категорий. Админ может добавить книги.", reply_markup=kb_main(is_admin(c.from_user.id)))
            await c.answer()
            return
        await c.message.edit_text("Категории:", reply_markup=kb_categories(cats_list))
        await c.answer()

    # open category
    @dp.callback_query(F.data.startswith("cat:"))
    async def open_cat(c: CallbackQuery):
        cat_id = c.data.split(":", 1)[1]
        catalog = load_catalog()
        cat = find_category(catalog, cat_id)
        if not cat:
            await c.answer("Категория не найдена", show_alert=True)
            return
        books = cat.get("books", [])
        if not books:
            await c.message.edit_text(f"Категория: {cat.get('title','')}\nПока пусто.", reply_markup=kb_categories(catalog.get("categories", [])))
            await c.answer()
            return
        await c.message.edit_text(f"Книги: {cat.get('title','')}", reply_markup=kb_books(cat_id, books))
        await c.answer()

    # open book
    @dp.callback_query(F.data.startswith("book:"))
    async def open_book(c: CallbackQuery):
        book_id = c.data.split(":", 1)[1]
        catalog = load_catalog()
        book = find_book(catalog, book_id)
        if not book:
            await c.answer("Книга не найдена", show_alert=True)
            return
        text = (
            f"📘 {book.get('title','')}\n"
            f"✍️ {book.get('author','')}\n"
            f"📄 Формат: {book.get('format','')}\n\n"
            f"{book.get('description','')}"
        )
        await c.message.edit_text(text, reply_markup=kb_book_actions(book_id))
        await c.answer()

    # download
    @dp.callback_query(F.data.startswith("dl:"))
    async def download(c: CallbackQuery):
        book_id = c.data.split(":", 1)[1]
        catalog = load_catalog()
        book = find_book(catalog, book_id)
        if not book:
            await c.answer("Книга не найдена", show_alert=True)
            return
        file_id = book.get("file_id")
        if not file_id:
            await c.answer("Файл не привязан", show_alert=True)
            return
        await c.answer()
        await c.message.answer_document(document=file_id, caption=f"{book.get('title','')} — {book.get('author','')}")

    # search ask
    @dp.callback_query(F.data == "search:ask")
    async def search_ask(c: CallbackQuery, state: FSMContext):
        await state.set_state(SearchFlow.waiting_query)
        await c.message.edit_text("Напишите слово для поиска (название или автор).")
        await c.answer()

    # search query
    @dp.message(SearchFlow.waiting_query, F.text)
    async def search_q(m: Message, state: FSMContext):
        q = m.text.strip()
        catalog = load_catalog()
        res = search_books(catalog, q)
        if not res:
            await m.answer("Ничего не нашёл. Попробуйте другое слово.", reply_markup=kb_main(is_admin(m.from_user.id)))
            await state.clear()
            return
        res = res[:15]
        lines = [f"• {b['title']} — {b.get('author','')} ({b.get('_category_title','')})" for b in res]
        await m.answer("Нашёл:\n" + "\n".join(lines) + "\n\nОткройте «Категории», чтобы скачать.", reply_markup=kb_main(is_admin(m.from_user.id)))
        await state.clear()

    # admin add start
    @dp.callback_query(F.data == "admin:add")
    async def admin_add(c: CallbackQuery, state: FSMContext):
        if not is_admin(c.from_user.id):
            await c.answer("Нет доступа", show_alert=True)
            return
        await state.set_state(AdminAddFlow.waiting_file)
        await c.message.edit_text("Админ: пришлите EPUB/PDF как файл (Document).\nОтмена: /cancel")
        await c.answer()

    @dp.message(F.text == "/cancel")
    async def cancel(m: Message, state: FSMContext):
        await state.clear()
        await m.answer("Отменено.", reply_markup=kb_main(is_admin(m.from_user.id)))

    # admin got file
    @dp.message(AdminAddFlow.waiting_file, F.document)
    async def admin_file(m: Message, state: FSMContext):
        if not is_admin(m.from_user.id):
            return
        doc = m.document
        file_id = doc.file_id
        name = doc.file_name or ""
        fmt = "EPUB" if name.lower().endswith(".epub") else ("PDF" if name.lower().endswith(".pdf") else (doc.mime_type or ""))

        await state.update_data(file_id=file_id, file_name=name, format=fmt)

        catalog = load_catalog()
        if not catalog.get("categories"):
            await m.answer("Категорий нет. Введите ID категории (латиница
