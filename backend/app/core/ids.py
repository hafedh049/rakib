"""Narrowing helper for Beanie document ids.

`Document.id` is `PydanticObjectId | None` because an unsaved document has no id.
Every document we hand to a response schema has already been persisted, so this
turns that runtime fact into a type the checker can see — and fails loudly rather
than silently serialising `null` if the invariant is ever broken.
"""

from beanie import Document, PydanticObjectId


def doc_id(document: Document) -> PydanticObjectId:
    if document.id is None:
        raise RuntimeError(
            f"{type(document).__name__} has no id — it was never persisted"
        )
    return document.id
