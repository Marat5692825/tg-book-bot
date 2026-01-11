from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .states import AdminAddFlow
from .catalog import (
    load_catalog, save_catalog, upsert_category,
    add_book_to_category, ensure_unique_book_id, slugify
)
from .keyboards import kb_admin_add_category, kb_main

router = Router()

def admin_only(user_id: int, admin_ids: set[int]) -> bool:
    return user_id in admin_ids

@router.callback_query(F.data == "admin:add_help")
async def admin_add_help(c: CallbackQuery, state: FSMContext, admin_ids: set[int]):
    if not admin_only(c.from_user.id, admin_ids):
        await c.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminAddFlow.waiting_file)
    await c.message.edit_text(
        "Админ-добавление:\n"
        "1) Пришлите EPUB/PDF как файл (Document) в этот чат.\n"
        "Можно переслать файл из другого чата.\n\n"
        "Чтобы отменить: /cancel"
    )
    await c.answer()

@router.message(F.text == "/cancel")
async def admin_cancel(m: Message, state: FSMContext, admin_ids: set[int]):
    if not admin_only(m.from_user.id, admin_ids):
        return
    await state.clear()
    await m.answer("Отменено.", reply_markup=kb_main(True))

@router.callback_query(F.data == "admin:cancel")
async def admin_cancel_cb(c: CallbackQuery, state: FSMContext, admin_ids: set[int]):
    if not admin_only(c.from_user.id, admin_ids):
        await c.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await c.message.edit_text("Отменено.", reply_markup=kb_main(True))
    await c.answer()

@router.message(AdminAddFlow.waiting_file, F.document)
async def admin_got_file(m: Message, state: FSMContext, admin_ids: set[int]):
    if not admin_only(m.from_user.id, admin_ids):
        return

    doc = m.document
    file_id = doc.file_id
    file_name = doc.file_name or ""
    mime = doc.mime_type or ""
    fmt = "EPUB" if file_name.lower().endswith(".epub") else ("PDF" if file_name.lower().endswith(".pdf") else mime)

    await state.update_data(file_id=file_id, file_name=file_name, format=fmt)

    catalog = load_catalog()
    cats = catalog.get("categories", [])
    await state.set_state(AdminAddFlow.waiting_cat_choice)

    if not cats:
        await m.answer(
            "Категорий пока нет. Создадим новую.\n"
            "Введите ID категории (латиница/цифры), например: aqidah"
        )
        await state.set_state(AdminAddFlow.waiting_new_cat_id)
        return

    await m.answer("Выберите категорию для книги:", reply_markup=kb_admin_add_category(cats))

@router.callback_query(AdminAddFlow.waiting_cat_choice, F.data.startswith("admin:set_cat:"))
async def admin_set_cat(c: CallbackQuery, state: FSMContext, admin_ids: set[int]):
    if not admin_only(c.from_user.id, admin_ids):
        await c.answer("Нет доступа", show_alert=True)
        return
    cat_id = c.data.split(":", 2)[2]
    await state.update_data(cat_id=cat_id)
    await state.set_state(AdminAddFlow.waiting_title)
    await c.message.edit_text("Введите название книги:")
    await c.answer()

@router.callback_query(AdminAddFlow.waiting_cat_choice, F.data == "admin:new_cat")
async def admin_new_cat(c: CallbackQuery, state: FSMContext, admin_ids: set[int]):
    if not admin_only(c.from_user.id, admin_ids):
        await c.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminAddFlow.waiting_new_cat_id)
    await c.message.edit_text("Введите ID новой категории (латиница/цифры), например: aqidah")
    await c.answer()

@router.message(AdminAddFlow.waiting_new_cat_id, F.text)
async def admin_new_cat_id(m: Message, state: FSMContext, admin_ids: set[int]):
    if not admin_only(m.from_user.id, admin_ids):
        return
    cat_id = m.text.strip().lower()
    if not cat_id or any(ch for ch in cat_id if not (ch.isalnum() or ch == "-")):
        await m.answer("ID должен быть только из латиницы/цифр/дефиса. Пример: aqidah")
        return
    await state.update_data(cat_id=cat_id)
    await state.set_state(AdminAddFlow.waiting_new_cat_title)
    await m.answer("Введите название категории (по-русски), например: Акыда")

@router.message(AdminAddFlow.waiting_new_cat_title, F.text)
async def admin_new_cat_title(m: Message, state: FSMContext, admin_ids: set[int]):
    if not admin_only(m.from_user.id, admin_ids):
        return
    title = m.text.strip()
    data = await state.get_data()
    cat_id = data["cat_id"]

    catalog = load_catalog()
    upsert_category(catalog, cat_id, title)
    save_catalog(catalog)

    await state.set_state(AdminAddFlow.waiting_title)
    await m.answer("Категория создана.\nТеперь введите название книги:")

@router.message(AdminAddFlow.waiting_title, F.text)
async def admin_title(m: Message, state: FSMContext, admin_ids: set[int]):
    if not admin_only(m.from_user.id, admin_ids):
        return
    await state.update_data(title=m.text.strip())
    await state.set_state(AdminAddFlow.waiting_author)
    await m.answer("Введите автора (или напишите “-”):")

@router.message(AdminAddFlow.waiting_author, F.text)
async def admin_author(m: Message, state: FSMContext, admin_ids: set[int]):
    if not admin_only(m.from_user.id, admin_ids):
        return
    author = m.text.strip()
    if author == "-":
        author = ""
    await state.update_data(author=author)
    await state.set_state(AdminAddFlow.waiting_description)
    await m.answer("Введите краткое описание (или “-”):")

@router.message(AdminAddFlow.waiting_description, F.text)
async def admin_description(m: Message, state: FSMContext, admin_ids: set[int]):
    if not admin_only(m.from_user.id, admin_ids):
        return
    desc = m.text.strip()
    if desc == "-":
        desc = ""

    data = await state.get_data()
    catalog = load_catalog()

    base_id = slugify(data.get("title", "book"))
    book_id = ensure_unique_book_id(catalog, base_id)

    book = {
        "id": book_id,
        "title": data.get("title", ""),
        "author": data.get("author", ""),
        "description": desc,
        "format": data.get("format", ""),
        "file_id": data.get("file_id", ""),
        "file_name": data.get("file_name", "")
    }

    cat_id = data["cat_id"]
    add_book_to_category(catalog, cat_id, book)
    save_catalog(catalog)

    await state.clear()
    await m.answer(
        "Готово. Книга добавлена:\n"
        f"ID: {book_id}\n"
        f"{book['title']} {('— ' + book['author']) if book['author'] else ''}\n"
        f"Категория: {cat_id}",
        reply_markup=kb_main(True)
    )
