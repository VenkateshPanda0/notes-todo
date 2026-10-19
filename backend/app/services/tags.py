import re

MAX_TAG_LENGTH = 32
MAX_TAGS_PER_ITEM = 20

# Letters, digits, underscore and hyphen (unicode letters allowed), starting with a letter.
_TAG_RE = re.compile(r"^[^\W\d_][\w-]*$")


def normalize_tags(raw: list[str]) -> list[str]:
    """Lowercase, strip a leading '#', validate and de-duplicate tags, preserving order."""
    result: list[str] = []
    for value in raw:
        name = value.strip().lstrip("#").lower()
        if not name:
            continue
        if len(name) > MAX_TAG_LENGTH or not _TAG_RE.match(name):
            raise ValueError(
                f"Invalid tag {value!r}: use letters, digits, '-' or '_' (starting with a letter), "
                f"up to {MAX_TAG_LENGTH} characters."
            )
        if name not in result:
            result.append(name)
    if len(result) > MAX_TAGS_PER_ITEM:
        raise ValueError(f"An item can have at most {MAX_TAGS_PER_ITEM} tags.")
    return result
