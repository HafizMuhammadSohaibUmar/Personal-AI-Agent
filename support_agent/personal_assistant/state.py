from typing import Annotated, Optional, TypedDict

from langgraph.graph import add_messages


class PersonalAssistantState(TypedDict, total=False):
    user_id: str
    user_question: str
    messages: Annotated[list, add_messages]
