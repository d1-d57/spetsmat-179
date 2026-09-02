"""§4, as a CARRIER: nothing personal is on the wire, checked against the real roster.

``core/services/raspoznavanie`` claimed this file existed before it did -- the §3
verifier's seventh finding.  The claim itself was true (it built the real request body
and got zero hits over 56 surnames and 56 given names), but a named carrier that is a
comment is a comment.  This is the carrier.

The check is a grep over the ACTUAL BYTES of the outgoing request, built by the same
``VisionModel._body`` production uses, against every surname and given name in
``seed/students.csv``.  It is not an inspection of the prompt template: a template can be
right while the caller passes the wrong list, and the wire is where the boundary is.
"""

from __future__ import annotations

import csv
import json

import config
from core.services.raspoznavanie import code_for_student
from infra.llm import VisionModel, build_prompt


def roster():
    """Every surname and given name of the real seed, as the words that must not appear."""
    words = []
    with (config.SEED_DIR / "students.csv").open(encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            for field in ("surname", "name"):
                value = (record.get(field) or "").strip()
                if len(value) > 2:
                    words.append(value)
    return words


def wire_body():
    """The request as it would actually be sent, minus the image bytes.

    The base64 image is dropped, not because it cannot carry a name, but because what it
    carries is settled elsewhere and by a different means: ``tools/blank.py --proba``
    proves the printed form has zero surnames on it, and that command exits 1 when it
    does not.  Two boundaries, two carriers.
    """
    students = list(range(1, 57))
    codes = [code_for_student(student_id) for student_id in students]
    labels = ["1", "2", "3а", "3б", "4", "5", "6", "7а", "7б", "8", "9", "10*", "11*"]
    sheets = [str(n) for n in range(1, 19)]

    model = VisionModel(api_key="k", post=lambda body: {})
    body = model._body(b"\x00" * 32, codes, labels, sheets)  # noqa: SLF001 -- the wire is the point
    for part in body["messages"][0]["content"]:
        if part.get("type") == "image_url":
            part["image_url"]["url"] = "data:image/jpeg;base64,<dropped>"
    return json.dumps(body, ensure_ascii=False)


def test_not_one_name_from_the_roster_reaches_the_wire(capsys):
    """Sending these abroad is a cross-border transfer of the data of fifty-six children.

    The answer is not «we delete it afterwards».  It is that the request contains no
    personal data, so there is no object of regulation at all.
    """
    payload = wire_body()
    words = roster()
    assert words, "the roster is empty; this check would be vacuous"

    leaked = sorted({word for word in words if word.lower() in payload.lower()})
    with capsys.disabled():
        print("\n[приватность] слов проверено %d из %d · найдено на проводе %d"
              % (len(words), len(words), len(leaked)))
    assert leaked == [], leaked


def test_the_check_can_go_red():
    """The negative control.  A grep that always answers «clean» proves nothing."""
    words = roster()
    a_name = sorted(words)[0]

    poisoned = wire_body() + " " + a_name
    leaked = sorted({word for word in words if word.lower() in poisoned.lower()})
    assert leaked == [a_name], leaked


def test_what_the_wire_carries_instead_is_codes():
    """Absence is only half of it: the request has to be USABLE without the names."""
    payload = wire_body()

    assert '"u1"' in payload and '"u56"' in payload
    assert "u17" in build_prompt(["u17"], ["1"])
    # The closed list is what makes a child the model does not have unnameable.
    body = json.loads(payload)
    enum = body["response_format"]["json_schema"]["schema"]["properties"]["rows"]["items"]\
        ["properties"]["student_code"]["enum"]
    assert len(enum) == 56
    assert all(value.startswith("u") and value[1:].isdigit() for value in enum)
