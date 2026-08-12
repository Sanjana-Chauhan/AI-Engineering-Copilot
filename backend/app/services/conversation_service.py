import uuid
from dataclasses import dataclass, field

MAX_HISTORY_TURNS = 10


@dataclass
class ConversationTurn:
    role: str
    content: str


@dataclass
class Conversation:
    repository_id: str
    turns: list[ConversationTurn] = field(default_factory=list)


_conversations: dict[str, Conversation] = {}


def new_conversation_id() -> str:
    return str(uuid.uuid4())


def get_history(conversation_id: str, repository_id: str) -> list[ConversationTurn]:
    conversation = _conversations.get(conversation_id)

    if conversation is None or conversation.repository_id != repository_id:
        return []

    return conversation.turns


def append_turn(
    conversation_id: str,
    repository_id: str,
    role: str,
    content: str
) -> None:
    conversation = _conversations.get(conversation_id)

    if conversation is None or conversation.repository_id != repository_id:
        conversation = Conversation(repository_id=repository_id)
        _conversations[conversation_id] = conversation

    conversation.turns.append(ConversationTurn(role=role, content=content))
    conversation.turns = conversation.turns[-MAX_HISTORY_TURNS * 2:]


def clear_conversation(conversation_id: str) -> None:
    _conversations.pop(conversation_id, None)
