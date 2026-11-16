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


def test_shopping_list_merges_and_deduplicates():
    r1 = client.post(
        "/recipes",
        json={"title": "Pancakes", "ingredients": ["flour", "milk", "eggs"], "tags": ["breakfast"]},
    )
    r2 = client.post(
        "/recipes",
        json={"title": "Waffles", "ingredients": ["flour", "sugar", "butter", "eggs"], "tags": ["breakfast"]},
    )
    r3 = client.post(
        "/recipes",
        json={"title": "Omelette", "ingredients": ["eggs", "cheese", "salt"], "tags": ["breakfast"]},
    )
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]
    id3 = r3.json()["id"]

    res = client.get(f"/shopping-list?ids={id1},{id2},{id3}")
    assert res.status_code == 200
    assert res.json() == ["flour", "milk", "eggs", "sugar", "butter", "cheese", "salt"]


def test_shopping_list_empty_or_no_ids():
    r_empty = client.get("/shopping-list")
    assert r_empty.status_code == 200
    assert r_empty.json() == []

    r_empty_param = client.get("/shopping-list?ids=")
    assert r_empty_param.status_code == 200
    assert r_empty_param.json() == []


def test_shopping_list_nonexistent_ids():
    r1 = client.post(
        "/recipes",
        json={"title": "Tea", "ingredients": ["water", "tea leaves"], "tags": ["drink"]},
    )
    id1 = r1.json()["id"]

    res = client.get(f"/shopping-list?ids={id1},99999")
    assert res.status_code == 200
    assert res.json() == ["water", "tea leaves"]

    res_none = client.get("/shopping-list?ids=99998,99999")
    assert res_none.status_code == 200
    assert res_none.json() == []


def test_shopping_list_formats_and_duplicates():
    r = client.post(
        "/recipes",
        json={"title": "Chili", "ingredients": ["beans", "beans", "tomato"], "tags": ["dinner"]},
    )
    rid = r.json()["id"]

    # Deduplicates within the same recipe
    res = client.get(f"/shopping-list?ids={rid}")
    assert res.status_code == 200
    assert res.json() == ["beans", "tomato"]

    # Comma with space
    res_space = client.get(f"/shopping-list?ids={rid}, {rid}")
    assert res_space.status_code == 200
    assert res_space.json() == ["beans", "tomato"]

    # Multiple query params (?ids=...&ids=...)
    res_multi = client.get(f"/shopping-list?ids={rid}&ids={rid}")
    assert res_multi.status_code == 200
    assert res_multi.json() == ["beans", "tomato"]
