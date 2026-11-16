from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_get_recipe():
    r = client.post(
        "/recipes",
        json={"title": "Pancakes", "ingredients": ["flour", "milk"], "tags": ["breakfast"]},
    )
    assert r.status_code == 200
    rid = r.json()["id"]
    r2 = client.get(f"/recipes/{rid}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Pancakes"
    assert r2.json()["tags"] == ["breakfast"]


def test_list_recipes():
    client.post("/recipes", json={"title": "Toast"})
    r = client.get("/recipes")
    assert r.status_code == 200
    assert any(rec["title"] == "Toast" for rec in r.json())


def test_unknown_recipe_404():
    r = client.get("/recipes/99999")
    assert r.status_code == 404


def test_filter_recipes_by_tag():
    client.post(
        "/recipes",
        json={"title": "Waffles", "ingredients": ["flour", "eggs"], "tags": ["breakfast", "sweet"]},
    )
    client.post(
        "/recipes",
        json={"title": "Spaghetti", "ingredients": ["pasta", "tomato"], "tags": ["dinner", "italian"]},
    )
    client.post(
        "/recipes",
        json={"title": "Omelette", "ingredients": ["eggs"], "tags": ["breakfast", "quick"]},
    )

    r = client.get("/recipes?tag=breakfast")
    assert r.status_code == 200
    recipes = r.json()
    assert len(recipes) >= 2
    assert all("breakfast" in rec["tags"] for rec in recipes)
    titles = [rec["title"] for rec in recipes]
    assert "Waffles" in titles
    assert "Omelette" in titles
    assert "Spaghetti" not in titles


def test_filter_recipes_by_tag_no_match():
    r = client.get("/recipes?tag=nonexistent_tag_12345")
    assert r.status_code == 200
    assert r.json() == []

