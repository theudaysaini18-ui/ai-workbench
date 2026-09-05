import re


CODING_KEYWORDS = {
    "python",
    "javascript",
    "typescript",
    "java",
    "c++",
    "cpp",
    "sql",
    "golang",
    "rust",
    "kotlin",
    "swift",
    "program",
    "programming",
    "code",
    "coding",
    "function",
    "class",
    "algorithm",
    "debug",
    "debugging",
    "refactor",
    "api",
    "regex",
    "script",
    "snippet",
    "fibonacci",
}

CODING_ACTIONS = {
    "write",
    "create",
    "build",
    "implement",
    "generate",
    "debug",
    "fix",
    "refactor",
    "explain",
    "review",
    "optimize",
    "convert",
}


def _normalize(message: str) -> str:
    """
    Normalize punctuation and whitespace while preserving code symbols
    such as +, #, and dots where useful.
    """
    text = str(message or "").lower()
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_coding_request(message: str) -> bool:
    """
    Detect common coding requests locally.

    This classifier intentionally favors routing to the coding agent when
    a programming language, coding term, or coding action is present.
    """
    normalized = _normalize(message)

    if not normalized:
        return False

    words = set(
        re.findall(
            r"[a-z0-9+#]+",
            normalized,
        )
    )

    has_coding_keyword = bool(words.intersection(CODING_KEYWORDS))
    has_coding_action = bool(words.intersection(CODING_ACTIONS))

    # Explicit programming-language request.
    if has_coding_keyword and has_coding_action:
        return True

    # Requests containing code/programming concepts are usually coding work.
    if len(words.intersection(CODING_KEYWORDS)) >= 2:
        return True

    # Common direct requests such as "write code" or "debug this".
    if "code" in words or "coding" in words or "debug" in words:
        return True

    return False


if __name__ == "__main__":
    test_cases = [
        "Write a Python program to generate Fibonacci numbers.",
        "write a python code for first 10 fibonacci numbers",
        "Can you debug this function?",
        "Create a JavaScript API example.",
        "What is local AI?",
        "Summarize this document.",
    ]

    for test_case in test_cases:
        print(is_coding_request(test_case), "->", test_case)