from collections import defaultdict
from threading import Lock


MAX_HISTORY_MESSAGES = 12


class SessionStore:
    """
    Simple in-memory conversation store.

    Each session has messages shaped like:
    {
        "role": "user" or "assistant",
        "content": "..."
    }
    """

    def __init__(self):
        self._sessions: dict[str, list[dict]] = defaultdict(list)
        self._lock = Lock()

    def get_history(self, session_id: str) -> list[dict]:
        """
        Return a copy of the newest messages in a session.

        Returning a copy prevents callers from changing stored conversation
        history accidentally.
        """
        with self._lock:
            return list(self._sessions[session_id][-MAX_HISTORY_MESSAGES:])

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Save one user or assistant message.

        Invalid roles are rejected so model message history stays valid.
        """
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")

        clean_content = content.strip()

        if not clean_content:
            return

        with self._lock:
            self._sessions[session_id].append(
                {
                    "role": role,
                    "content": clean_content,
                }
            )

            # Keep memory bounded so prompt length and RAM do not grow forever.
            self._sessions[session_id] = self._sessions[session_id][
                -MAX_HISTORY_MESSAGES:
            ]

    def clear_session(self, session_id: str) -> None:
        """Delete conversation history for one session."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        """Returns how many active in-memory sessions exist."""
        with self._lock:
            return len(self._sessions)


if __name__ == "__main__":
    store = SessionStore()

    store.add_message(
        session_id="demo-session",
        role="user",
        content="Explain what a local LLM is.",
    )

    store.add_message(
        session_id="demo-session",
        role="assistant",
        content=(
            "A local LLM is a language model that runs on your own "
            "computer or organization server."
        ),
    )

    store.add_message(
        session_id="demo-session",
        role="user",
        content="Why is that useful for confidential documents?",
    )

    print("History:")
    for message in store.get_history("demo-session"):
        print(f"{message['role']}: {message['content']}")

    print("\nActive sessions:", store.session_count())

    store.clear_session("demo-session")
    print("Sessions after clear:", store.session_count())