from aiogram.fsm.state import StatesGroup, State

class SearchFlow(StatesGroup):
    waiting_query = State()

class AdminAddFlow(StatesGroup):
    waiting_file = State()
    waiting_cat_choice = State()
    waiting_new_cat_id = State()
    waiting_new_cat_title = State()
    waiting_title = State()
    waiting_author = State()
    waiting_description = State()
