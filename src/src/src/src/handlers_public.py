from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .catalog import load_catalog, get_category, get_book, search_books
from .keyboards import kb_main, kb_categories, kb_books, kb_book_actions
from .states import SearchFlow

router = Router()

def is_admin(user_id: int, admin_ids: set[int]) -> bool:
    return user_id in admin_ids

@router.message(F.text.in_({"/start", "/help"}))
async def cmd_start(m: Message, state: FSMContext, admin_ids: set[int]):
    await state.clear()
    await m.answer(
        "Ассаляму алейкум.\nЭто библиотека книг.\nВыберите действие:",
        reply_markup=kb_main(is_admin(m.from_user.id, admin_ids))
    )

@router.callback_query(F.data == "home")
async def cb_home(c: CallbackQuery, state: FSMContext, admin_ids: set[int]):
    await state.clear()
    await c.message.edit_text(
        "Выберите действие:",
        reply_markup=kb_main(is_admin(c.from_user.id, admin_ids))
    )
    await c.answer()

@router.callback_query(F.data == "cats")
async def cb_categories(c: CallbackQuery, admin_ids: set[int]):
    catalog = load_catalog()
    cats = catalog.get("categories", [])
    if not cats:
        await c.message.edit_text(
            "Пока нет категорий. Админ может добавить книги.",
            reply_markup=kb_main(is_admin(c.from_user.id, admin_ids))
        )
        await c.answer()
        return
    await c.message.edit_text("Категории:", reply_markup=kb_categories(cats))
    await c.answer()

@router.callback_query(F.data.startswith("cat:"))
async def cb_cat(c: CallbackQuery, admin_ids: set[int]):
    cat_id = c.data.split(":", 1)[1]
    catalog = load_catalog()
    cat = get_category(catalog, cat_id)
    if not cat:
        await c.answer("Категория не найдена", show_alert=True)
        return
    books = cat.get("books", [])
    if not books:
        await c.message.edit_text(
            f"Категория: {cat['title']}\nПока пусто.",
            reply_markup=kb_categories(catalog.get("categories", []))
        )
        await c.answer()
        return
    await c.message.edit_text(f"Книги: {cat['title']}", reply_markup=kb_books(books))
    await c.answer()

@router.callback_query(F.data.startswith("book:"))
async def cb_book(c: CallbackQuery):
    book_id = c.data.split(":", 1)[1]
    catalog = load_catalog()
    book = get_book(catalog, book_id)
    if not book:
        await c.answer("Книга не найдена", show_alert=True)
        return
    text = (
        f"📘 {book.get('title')}\n"
        f"✍️ {book.get('author','')}\n"
        f"📄 Формат: {book.get('format','')}\n\n"
        f"{book.get('description','')}"
    )
    await c.message.edit_text(text, reply_markup=kb_book_actions(book_id))
    await c.answer()

@router.callback_query(F.data.startswith("dl:"))
async def cb_download(c: CallbackQuery):
    book_id = c.data.split(":", 1)[1]
    catalog = load_catalog()
    book = get_book(catalog, book_id)
    if not book:
        await c.answer("Книга не найдена", show_alert=True)
        return

    file_id = book.get("file_id")
    if not file_id:
        await c.answer("Файл не привязан (нет file_id)", show_alert=True)
        return

    await c.answer()
    await c.message.answer_document(
        document=file_id,
        caption=f"{book.get('title')} — {book.get('author','')}"
    )

@router.callback_query(F.data == "search:ask")
async def cb_search_ask(c: CallbackQuery, state: FSMContext):
    await state.set_state(SearchFlow.waiting_query)
    await c.message.edit_text("Напишите слово для поиска (название или автор).")
    await c.answer()

@router.message(SearchFlow.waiting_query, F.text)
async def msg_search(m: Message, state: FSMContext, admin_ids: set[int]):
    q = m.text.strip()
    catalog = load_catalog()
    results = search_books(catalog, q)

    if not results:
        await m.answer(
            "Ничего не нашёл. Попробуйте другое слово.",
            reply_markup=kb_main(is_admin(m.from_user.id, admin_ids))
        )
        await state.clear()
        return

    results = results[:15]
    lines = [f"• {b['title']} — {b.get('author','')} ({b.get('_category_title','')})" for b in results]
    await m.answer(
        "Нашёл:\n" + "\n".join(lines) + "\n\nОткройте «Категории», чтобы скачать.",
        reply_markup=kb_main(is_admin(m.from_user.id, admin_ids))
    )
    await state.clear()
