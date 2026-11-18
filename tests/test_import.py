"""Adventure import (M6d): upload and extraction, conversion to a bible, the spoiler-free review, cancel, and the
author's text per Location. Driven through the server (Seam 4) with FakeClaude."""

from __future__ import annotations

import io

from sqlalchemy import text as sql

from d_and_deez.models import Campaign, Source

from conftest import SETUP, bible_call, campaigns, fixture_bible, start, text  # noqa: F401 (server fixture)

ADVENTURE = """# The Drowned Bell

A one-shot for level 1 characters.

## The Reed Shore

Read aloud: Fog lies on the Reed Shore like wet wool.

## The abandoned tide mill

The mill wheel groans. Hesta's ledger hides under the third floorboard.

## Old Hesta

A wiry ferrywoman who knows more than she says.
"""


def pdf(body: str | None) -> bytes:
    """A one-page PDF; with no `body` the page has no text layer (a scan)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({body}) Tj ET" if body else ""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for n, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{n} 0 obj\n{o}\nendobj\n".encode())
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    out.writelines(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


def upload(s, name="bell.md", data=ADVENTURE.encode()):
    return s.http.post("/sources", params={"filename": name}, content=data)


def chunks(factory, source_id):
    with factory() as db:
        return [tuple(r) for r in db.execute(sql("SELECT heading, kind, ref FROM source_chunks WHERE source_id = :s "
                                                 "ORDER BY rowid"), {"s": source_id})]


def import_campaign(s, source_id, **overrides) -> int:
    s.plan.script.append(bible_call())
    r = s.http.post("/campaigns", json={"template": "rogue", "source_id": source_id, **overrides})
    assert r.status_code == 202, r.text
    return r.json()["campaign_id"]


# --- upload and extraction ----------------------------------------------------------------------

def test_a_text_upload_is_stored_locally_and_split_by_heading(server, factory):
    r = upload(server)
    assert r.status_code == 200
    sid = r.json()["source_id"]
    assert [h for h, _, _ in chunks(factory, sid)] == ["The Drowned Bell", "The Reed Shore",
                                                       "The abandoned tide mill", "Old Hesta"]
    with factory() as db:
        src = db.get(Source, sid)
        assert src.title == "bell" and len(src.sha256) == 64
    assert [p.read_bytes() for p in server.sources.iterdir()] == [ADVENTURE.encode()]


def test_a_pdf_with_a_text_layer_is_extracted(server, factory):
    r = upload(server, "bell.pdf", pdf("The Reed Shore is foggy"))
    assert r.status_code == 200
    with factory() as db:
        body = db.scalar(sql("SELECT body FROM source_chunks WHERE source_id = :s"), {"s": r.json()["source_id"]})
    assert "Reed Shore is foggy" in body


def test_a_pdf_with_no_text_layer_is_rejected_and_nothing_is_stored(server, factory):
    r = upload(server, "scan.pdf", pdf(None))
    assert r.status_code == 400 and "no text layer" in r.json()["detail"]
    with factory() as db:
        assert db.query(Source).count() == 0
        assert db.scalar(sql("SELECT count(*) FROM source_chunks")) == 0
    assert not server.sources.exists() or not list(server.sources.iterdir())


def test_other_uploads_are_rejected_with_a_reason(server):
    assert "PDF, Markdown or text" in upload(server, "bell.docx").json()["detail"]
    assert "could not be read" in upload(server, "bad.pdf", b"not a pdf").json()["detail"]
    assert "not UTF-8" in upload(server, "bell.txt", b"\xff\xfe\x00bad").json()["detail"]
    assert "empty" in upload(server, "bell.txt", b"  \n").json()["detail"]


# --- conversion and review ----------------------------------------------------------------------

def test_an_imported_adventure_becomes_a_ready_campaign_with_a_spoiler_free_review(server, factory):
    sid = upload(server).json()["source_id"]
    cid = import_campaign(server, sid, lines="spiders")
    c = campaigns(server)[cid]
    assert c["status"] == "ready" and c["source_id"] == sid
    assert c["summary"] == {"acts": 1, "npcs": 3, "locations": 4}
    assert len(c["warnings"]) == 1 and "party of four" in c["warnings"][0]
    assert "Fog lies" not in str(c) and "secret.rope" not in str(c)
    request = server.plan.requests[0]
    assert "Fog lies on the Reed Shore" in request["messages"][0]["content"]  # Claude gets the text, once
    assert "Lines (never shown): spiders" in request["messages"][0]["content"]
    with factory() as db:
        camp = db.get(Campaign, cid)
        assert camp.length == "imported" and camp.character.name and len(camp.beats) == 3  # seeded as a generated one


def test_the_converted_bible_passes_the_generated_schema_and_a_bad_one_is_retried(server):
    sid = upload(server).json()["source_id"]
    bad = fixture_bible()
    bad["clues"] = bad["clues"][:1]
    server.plan.script.append(bible_call(bad))
    cid = import_campaign(server, sid)
    assert campaigns(server)[cid]["status"] == "ready"
    assert "Three Clue Rule" in str(server.plan.requests[1]["messages"][-1]["content"])


def test_a_bible_that_never_validates_fails_the_campaign_and_keeps_the_source(server, factory):
    sid = upload(server).json()["source_id"]
    bad = fixture_bible()
    bad["clocks"] = []
    server.plan.script.extend([bible_call(bad)] * 3)
    r = server.http.post("/campaigns", json={"template": "rogue", "source_id": sid})
    c = campaigns(server)[r.json()["campaign_id"]]
    assert c["status"] == "failed" and "Main clock" in c["setup_error"]
    assert chunks(factory, sid)


def test_chunks_are_tied_to_the_locations_and_npcs_their_headings_name(server, factory):
    sid = upload(server).json()["source_id"]
    import_campaign(server, sid)
    assert chunks(factory, sid) == [("The Drowned Bell", "section", ""), ("The Reed Shore", "location", "loc.shore"),
                                        ("The abandoned tide mill", "location", "loc.mill"),
                                        ("Old Hesta", "npc", "Old Hesta")]


def test_a_source_has_one_campaign_and_an_unknown_source_is_refused(server):
    sid = upload(server).json()["source_id"]
    import_campaign(server, sid)
    assert server.http.post("/campaigns", json={"template": "rogue", "source_id": sid}).status_code == 409
    assert server.http.post("/campaigns", json={"template": "rogue", "source_id": 99}).status_code == 404
    assert server.http.post("/campaigns", json={"template": "rogue"}).status_code == 422  # generated needs setting


# --- accept, cancel -----------------------------------------------------------------------------

def test_cancelling_a_ready_import_deletes_the_source_its_file_and_the_campaign(server, factory):
    sid = upload(server).json()["source_id"]
    cid = import_campaign(server, sid)
    assert server.http.delete(f"/sources/{sid}").status_code == 200
    assert cid not in campaigns(server)
    with factory() as db:
        assert db.query(Source).count() == 0
        assert db.scalar(sql("SELECT count(*) FROM source_chunks")) == 0
    assert list(server.sources.iterdir()) == []
    assert server.http.delete(f"/sources/{sid}").status_code == 404


def test_cancelling_after_accepting_is_refused(server, factory):
    sid = upload(server).json()["source_id"]
    start(server, import_campaign(server, sid))
    assert server.http.delete(f"/sources/{sid}").status_code == 409
    assert chunks(factory, sid)


def test_a_cancelled_upload_with_no_campaign_is_deleted_too(server, factory):
    sid = upload(server).json()["source_id"]
    assert server.http.delete(f"/sources/{sid}").status_code == 200
    assert chunks(factory, sid) == []


def test_regenerating_an_import_converts_the_same_source_again(server, factory):
    sid = upload(server).json()["source_id"]
    cid = import_campaign(server, sid)
    server.plan.script.append(bible_call())
    assert server.http.post(f"/campaigns/{cid}/regenerate").status_code == 202
    assert "<adventure>" in server.plan.requests[1]["messages"][0]["content"]
    assert campaigns(server)[cid]["status"] == "ready"


# --- play ---------------------------------------------------------------------------------------

def test_a_turn_carries_only_the_authors_text_for_the_current_location(server):
    sid = upload(server).json()["source_id"]
    cid = import_campaign(server, sid)
    start(server, cid)
    first = server.turn.requests[0]["messages"][-1]["content"][0]["text"]
    assert "<source>" in first and "Fog lies on the Reed Shore" in first
    assert "wheel groans" not in first and "Hesta" not in first.split("<source>")[1].split("</source>")[0]


def test_a_generated_campaign_has_no_source_block(server):
    from conftest import create
    start(server, create(server))
    assert "<source>" not in server.turn.requests[0]["messages"][-1]["content"][0]["text"]


def test_moving_swaps_the_source_text_and_the_ui_never_carries_it(server):
    from conftest import act, tool
    sid = upload(server).json()["source_id"]
    cid = import_campaign(server, sid)
    session = start(server, cid)
    act(server, "I go to the mill.", tool("move_to", location="loc.mill"), text("The wheel groans."))
    act(server, "I look around.")
    ctx = server.turn.requests[-1]["messages"][-1]["content"][0]["text"]
    assert "wheel groans" in ctx.split("<source>")[1].split("</source>")[0] and "Fog lies" not in ctx
    ui = server.http.get("/state").text + server.http.get("/log", params={"session": session}).text
    assert "third floorboard" not in ui and "Fog lies on the Reed Shore like wet wool" not in ui
