"""商品模块接口测试：列表 / 详情 / 13001。"""

from __future__ import annotations


def test_list_products(client):
    resp = client.get("/api/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["page"] == 1
    assert data["pageSize"] == 20
    assert data["total"] >= 2
    names = {item["name"] for item in data["list"]}
    assert "单人测算报告" in names
    assert "单人测算报告（免费版）" in names
    paid = [i for i in data["list"] if i["name"] == "单人测算报告"][0]
    assert paid["price"] == 9900
    assert paid["type"] == 1
    assert paid["freeFlag"] == 0
    assert paid["status"] == 1


def test_list_products_type_filter(client):
    resp = client.get("/api/products", params={"type": 1})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert all(item["type"] == 1 for item in data["list"])
    assert len(data["list"]) == 1

    resp = client.get("/api/products", params={"type": 0})
    data = resp.json()["data"]
    assert all(item["type"] == 0 for item in data["list"])
    assert len(data["list"]) == 1


def test_list_products_pagination(client):
    resp = client.get("/api/products", params={"page": 1, "pageSize": 1})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page"] == 1
    assert data["pageSize"] == 1
    assert len(data["list"]) == 1
    assert data["total"] == 2


def test_get_product(client):
    resp = client.get("/api/products/1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["id"] == 1
    assert data["name"] == "单人测算报告"
    assert data["price"] == 9900


def test_get_product_not_found_13001(client):
    resp = client.get("/api/products/99999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 13001
    assert body["data"] is None
