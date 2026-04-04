import json

from app.api.v1.predict import get_predict_service


class FakePredictService:
    def run_stream(self, text: str, session_id: str):
        extraction = {
            "intent": "data_query",
            "entities": {
                "category": "skincare",
                "target": "gen z",
                "price_max": 100000,
            },
        }

        result = {
            "pipeline_version": 4,
            "input": text,
            "extraction": extraction,
            "mode": "query_table",
            "process": [],
            "tool_results": [
                {
                    "tool": "query_table",
                    "args": {
                        "plan": {
                            "source": {"table": "product.products", "alias": "p"},
                            "select": [{"field": "p.name"}],
                            "filters": [{"field": "p.category", "op": "ilike", "value": "skincare"}],
                            "metadata_hash": "fakehash",
                        },
                    },
                    "data": {
                        "query_kind": "query_table",
                        "join_count": 0,
                        "subquery_count": 0,
                        "row_count": 1,
                        "rows": [{"id": 1, "name": "Glow Serum"}],
                        "metadata_hash": "fakehash",
                        "metadata_version": "fakehash1234",
                    },
                }
            ],
            "message": "Found 1 result(s).",
            "metadata_snapshot_hash": "fakehash",
            "metadata_snapshot_version": "fakehash1234",
        }

        yield f"event: extraction\ndata: {json.dumps(extraction)}\n\n"
        yield f"event: result\ndata: {json.dumps(result)}\n\n"
        yield "event: done\ndata: {}\n\n"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_stream(client):
    client.app.dependency_overrides[get_predict_service] = lambda: FakePredictService()

    response = client.post("/predict", json={"text": "show me skincare for gen z under 100k"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    assert "event: extraction" in body
    assert "event: result" in body
    assert "event: done" in body
    assert '"intent": "data_query"' in body
