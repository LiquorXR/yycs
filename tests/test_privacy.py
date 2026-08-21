"""隐私协议相关接口测试：版本校验、版本接口、客服删除。"""

from __future__ import annotations

from tests.conftest import VALID_PROFILE, create_profile


def test_privacy_version(client):
    resp = client.get("/api/privacy/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["version"] == "v1.0"
    assert data["effectiveDate"] == "2026-08-21"
    assert data["companyName"] == "四川蜀兴振凡传媒有限公司"
    assert data["icpNo"] == "蜀ICP备2026047533号"
    assert "contactEmail" in data
    assert data["retentionDaysUnpaid"] == 30
    assert data["retentionDaysPaid"] == 365


def test_create_profile_missing_privacy_version_10001(client):
    payload = dict(VALID_PROFILE)
    payload.pop("agreedPrivacyVersion", None)
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-no-version"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 10001


def test_create_profile_wrong_privacy_version_10001(client):
    payload = dict(VALID_PROFILE, agreedPrivacyVersion="v0.9")
    resp = client.post("/api/profiles", json=payload, headers={"Idempotency-Key": "k-wrong-version"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 10001


def test_create_profile_with_correct_version_success(client):
    resp = client.post("/api/profiles", json=VALID_PROFILE, headers={"Idempotency-Key": "k-correct-version"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_delete_profile_anonimizes(client):
    data = create_profile(client, _key="k-del-test")
    pid = data["profileId"]
    # 删除前预览正常
    resp = client.get(f"/api/profiles/{pid}/preview")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "张三"

    # 客服删除
    del_resp = client.delete(f"/api/profiles/{pid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # 删除后预览返回已删除占位
    resp2 = client.get(f"/api/profiles/{pid}/preview")
    assert resp2.status_code == 200
    assert resp2.json()["data"]["name"] == "已删除"
    assert resp2.json()["data"]["birth"] == "1900-01-01"


def test_delete_profile_not_found_10004(client):
    resp = client.delete("/api/profiles/P99999999")
    assert resp.status_code == 404
    assert resp.json()["code"] == 10004
