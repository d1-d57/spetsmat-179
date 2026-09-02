"""§2 at the router: which of Telegram's offered sizes is fetched, and what is refused.

``test_flow.py`` stubs the download out, because the flow is not about Telegram's file
API; this file is the other half, and it is the one that would catch «the bot asks for a
file it cannot have».
"""

from __future__ import annotations

import asyncio

import pytest

from bot.routers.photo import _download
from core.services.raspoznavanie import MAX_DOWNLOAD_BYTES, IntakeRefused


class FakeBot:
    """Just enough of a bot to answer ``download``: which file_id was asked for."""

    def __init__(self) -> None:
        self.asked = None

    async def download(self, file_id, destination):
        self.asked = file_id
        destination.write(b"bytes-of-%s" % file_id.encode())


class Size:
    def __init__(self, file_id, width, height, file_size):
        self.file_id, self.width, self.height, self.file_size = (
            file_id, width, height, file_size
        )


class FakeMessage:
    def __init__(self, photo=None, document=None):
        self.photo, self.document = photo or [], document


class Document:
    def __init__(self, file_id, file_size, mime_type="image/jpeg"):
        self.file_id, self.file_size, self.mime_type = file_id, file_size, mime_type


def run(coroutine):
    """Run one coroutine and CLOSE the loop.

    ``pyproject.toml`` turns every warning into an error, and a leaked loop raises a
    ``ResourceWarning`` at collection time -- which pytest attributes to whichever test
    happens to be running when the garbage collector gets to it, i.e. to an innocent one
    in another file.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


def test_the_largest_offered_size_that_getfile_can_fetch_is_taken():
    """A photo arrives as an ARRAY of sizes; the original does not exist anywhere.

    Compression is always client-side, so «ask for the original» is not an option -- the
    ceiling is 2560 px with the sender's HD toggle on and 1280 without it.
    """
    bot = FakeBot()
    message = FakeMessage(photo=[
        Size("small", 320, 180, 9_000),
        Size("medium", 1280, 720, 300_000),
        Size("large", 2560, 1440, 900_000),
    ])

    assert run(_download(message, bot)) == b"bytes-of-large"
    assert bot.asked == "large"


def test_a_size_over_the_ceiling_is_skipped_in_favour_of_one_that_fits():
    bot = FakeBot()
    message = FakeMessage(photo=[
        Size("medium", 1280, 720, 300_000),
        Size("huge", 2560, 1440, MAX_DOWNLOAD_BYTES + 1),
    ])

    assert run(_download(message, bot)) == b"bytes-of-medium"


def test_a_photo_whose_every_size_is_over_the_ceiling_is_refused_in_a_sentence():
    bot = FakeBot()
    message = FakeMessage(photo=[Size("huge", 2560, 1440, MAX_DOWNLOAD_BYTES + 1)])

    with pytest.raises(IntakeRefused):
        run(_download(message, bot))
    assert bot.asked is None, "the bot asked for a file getFile cannot give it"


def test_a_document_is_fetched_whole_and_the_same_ceiling_applies():
    """A document is worth asking for when the sheet was shot from far away.

    The gain is not resolution -- the pipeline downscales anyway -- but the absence of a
    second JPEG generation.
    """
    bot = FakeBot()
    assert run(_download(FakeMessage(document=Document("doc", 5_000_000)), bot)) \
        == b"bytes-of-doc"

    with pytest.raises(IntakeRefused):
        run(_download(FakeMessage(document=Document("big", MAX_DOWNLOAD_BYTES + 1)), bot))
