"""FSM states for the registration flow.

Two states per role: surname, then name.  The owner-side moderation has no
FSM -- each button press carries the registration id in its callback data.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class StudentRegistration(StatesGroup):
    waiting_for_surname = State()
    waiting_for_name = State()


class TeacherRegistration(StatesGroup):
    waiting_for_surname = State()
    waiting_for_name = State()
    waiting_for_room = State()