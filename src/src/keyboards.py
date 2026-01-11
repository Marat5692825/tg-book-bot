from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb_main(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Категории", callback_data="cats")],
        [InlineKeyboardButton(text="Поиск", callback_data="search:ask")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="➕ Добавить книгу (админ)", callback_data="admin:add_help")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_categories(categories: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=c["title"], callback_data=f"cat:{c['id']}")] for c in categories]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_books(books: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=b["title"], callback_data=f"book:{b['id']}")] for b in books]
    rows.append([InlineKeyboardButton(text="⬅️ Категории", callback_data="cats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_book_actions(book_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать", callback_data=f"dl:{book_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="cats")],
    ])

def kb_admin_add_category(cats: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=c["title"], callback_data=f"admin:set_cat:{c['id']}")] for c in cats]
    rows.append([InlineKeyboardButton(text="➕ Новая категория", callback_data="admin:new_cat")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
