import asyncio
from types import SimpleNamespace
from uuid import uuid4

from app.services.ai.embedding_client import embedding_client
from app.services.ai.matching_service import matching_service


class _FakeResult:
    def __init__(self, lead=None, rows=None):
        self._lead = lead
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._lead

    def all(self):
        return self._rows


class _FakeDBNoLead:
    async def execute(self, _stmt):
        return _FakeResult(lead=None)


def test_matching_returns_empty_when_lead_missing():
    result = asyncio.run(matching_service.find_matches(uuid4(), _FakeDBNoLead()))
    assert result == []


def test_matching_formats_similarity_output(monkeypatch):
    async def _fake_embed(_text):
        return [0.1] * 384

    monkeypatch.setattr("app.services.ai.matching_service.embedding_client.embed", _fake_embed)

    lead = SimpleNamespace(
        id=uuid4(),
        intake_data={"shoot_type": "commercial", "location_type": "studio", "requirements": "natural light"},
    )
    loc = SimpleNamespace(id=uuid4(), name="Test Studio", type="studio", address="Mumbai")

    class _FakeDB:
        def __init__(self):
            self.calls = 0

        async def execute(self, _stmt):
            self.calls += 1
            if self.calls == 1:
                return _FakeResult(lead=lead)
            return _FakeResult(rows=[(loc, 0.2)])

    matches = asyncio.run(matching_service.find_matches(lead.id, _FakeDB()))
    assert len(matches) == 1
    assert matches[0]["name"] == "Test Studio"
    assert matches[0]["similarity"] == 0.8


def test_embedding_dimension_is_384():
    vector = asyncio.run(embedding_client.embed("cinematic rooftop sunset"))
    assert len(vector) == 384


def test_similarity_ranking_descends_with_distance(monkeypatch):
    async def _fake_embed(_text):
        return [0.1] * 384

    monkeypatch.setattr("app.services.ai.matching_service.embedding_client.embed", _fake_embed)

    lead = SimpleNamespace(
        id=uuid4(),
        intake_data={
            "shoot_type": "music video",
            "location_type": "outdoor",
            "requirements": "wide skyline",
        },
    )
    first = SimpleNamespace(id=uuid4(), name="Top Match", type="outdoor", address="A")
    second = SimpleNamespace(id=uuid4(), name="Lower Match", type="outdoor", address="B")

    class _FakeDB:
        def __init__(self):
            self.calls = 0

        async def execute(self, _stmt):
            self.calls += 1
            if self.calls == 1:
                return _FakeResult(lead=lead)
            return _FakeResult(rows=[(first, 0.1), (second, 0.6)])

    ranked = asyncio.run(matching_service.find_matches(lead.id, _FakeDB()))
    assert ranked[0]["name"] == "Top Match"
    assert ranked[0]["similarity"] > ranked[1]["similarity"]


def test_empty_input_embedding_is_handled():
    vector = asyncio.run(embedding_client.embed(""))
    assert len(vector) == 384
