"""测算模块接口测试：校验失败 14001 / 成功创建 / preview 10004 / 脱敏字段。"""

from __future__ import annotations

from tests.conftest import VALID_PROFILE, create_profile


def test_create_profile_success(client):
    resp = client.post("/api/profiles", json=VALID_PROFILE, headers={"Idempotency-Key": "k-create"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["profileId"].startswith("P")
    preview = data["previewReport"]
    assert preview["locked"] is True
    assert preview["lockedNote"] == "完整版需付费解锁"
    assert preview["title"] == "张三 · 姻缘运势测算预览"
    assert preview["contentUrl"].endswith("_preview.html")


def test_create_profile_without_birth_hour(client):
    payload = dict(VALID_PROFILE, birthHour=None)
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-nohour"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_create_profile_with_focus_tags(client):
    payload = dict(VALID_PROFILE, focusTags=["正缘桃花期", "婚后财运旺衰"])
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-tags"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_create_profile_name_too_short_14001(client):
    payload = dict(VALID_PROFILE, name="张")
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-short"})
    assert resp.status_code == 422
    assert resp.json()["code"] == 14001


def test_create_profile_name_too_long_14001(client):
    payload = dict(VALID_PROFILE, name="张" * 21)
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-long"})
    assert resp.status_code == 422
    assert resp.json()["code"] == 14001


def test_create_profile_invalid_date_14001(client):
    payload = dict(VALID_PROFILE, birth="1995-13-40")
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-date"})
    assert resp.status_code == 422
    assert resp.json()["code"] == 14001


def test_create_profile_date_in_future_14001(client):
    payload = dict(VALID_PROFILE, birth="2099-01-01")
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-future"})
    assert resp.status_code == 422
    assert resp.json()["code"] == 14001


def test_create_profile_bad_hour_14001(client):
    payload = dict(VALID_PROFILE, birthHour="亥丑")
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-hour"})
    assert resp.status_code == 422
    assert resp.json()["code"] == 14001


def test_create_profile_idempotent(client):
    key = "idem-profile"
    first = client.post("/api/profiles", json=VALID_PROFILE, headers={"Idempotency-Key": key}).json()["data"]
    second = client.post("/api/profiles", json=VALID_PROFILE, headers={"Idempotency-Key": key}).json()["data"]
    assert second == first


def test_preview_not_found_10004(client):
    resp = client.get("/api/profiles/P99999999/preview")
    assert resp.status_code == 404
    assert resp.json()["code"] == 10004


def test_preview_returns_masked(client):
    data = create_profile(client, _key="k-prev")
    profile_id = data["profileId"]
    resp = client.get(f"/api/profiles/{profile_id}/preview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    d = body["data"]
    assert d["name"] == "张三"
    assert d["birth"] == "1995-08-15"
    preview = d["previewReport"]
    assert preview["locked"] is True
    assert preview["contentUrl"].endswith("_preview.html")
    # 脱敏：响应不含密文
    raw = resp.text
    assert "gAAAA" not in raw
