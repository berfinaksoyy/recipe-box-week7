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


def test_scale_recipe_integers():
    post_res = client.post(
        "/recipes",
        json={"title": "Cake", "ingredients": ["200 g flour", "2 eggs", "100 ml milk"], "tags": ["dessert"]},
    )
    rid = post_res.json()["id"]

    res = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert res.status_code == 200
    assert res.json() == {
        "id": rid,
        "title": "Cake",
        "ingredients": ["400 g flour", "4 eggs", "200 ml milk"],
        "tags": ["dessert"],
    }


def test_scale_recipe_decimals():
    post_res = client.post(
        "/recipes",
        json={"title": "Pudding", "ingredients": ["1.5 cups milk", "0.5 tsp vanilla"]},
    )
    rid = post_res.json()["id"]

    # Scaling factor 2 produces whole numbers without .0
    res_factor2 = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert res_factor2.status_code == 200
    assert res_factor2.json()["ingredients"] == ["3 cups milk", "1 tsp vanilla"]

    # Scaling factor 3 produces decimals
    res_factor3 = client.get(f"/recipes/{rid}/scaled?factor=3")
    assert res_factor3.status_code == 200
    assert res_factor3.json()["ingredients"] == ["4.5 cups milk", "1.5 tsp vanilla"]


def test_scale_recipe_simple_fractions():
    post_res = client.post(
        "/recipes",
        json={"title": "Bread", "ingredients": ["1/2 tsp salt", "3/4 cup sugar"]},
    )
    rid = post_res.json()["id"]

    res_factor2 = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert res_factor2.status_code == 200
    assert res_factor2.json()["ingredients"] == ["1 tsp salt", "1.5 cup sugar"]

    res_factor3 = client.get(f"/recipes/{rid}/scaled?factor=3")
    assert res_factor3.status_code == 200
    assert res_factor3.json()["ingredients"] == ["1.5 tsp salt", "2.25 cup sugar"]


def test_scale_recipe_without_leading_numbers():
    post_res = client.post(
        "/recipes",
        json={"title": "Salad", "ingredients": ["salt to taste", "freshly ground black pepper", "olive oil"]},
    )
    rid = post_res.json()["id"]

    res = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert res.status_code == 200
    assert res.json()["ingredients"] == ["salt to taste", "freshly ground black pepper", "olive oil"]


def test_scale_recipe_readable_results_no_float_noise_and_no_dot_zero():
    post_res = client.post(
        "/recipes",
        json={"title": "Risotto", "ingredients": ["0.1 g saffron", "1.5 cups water"]},
    )
    rid = post_res.json()["id"]

    # 0.1 * 3 in floating point is 0.30000000000000004; must be cleaned to 0.3
    res_factor3 = client.get(f"/recipes/{rid}/scaled?factor=3")
    assert res_factor3.status_code == 200
    assert res_factor3.json()["ingredients"] == ["0.3 g saffron", "4.5 cups water"]

    # Whole number scaling must not produce .0 (e.g. 3, not 3.0)
    res_factor2 = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert res_factor2.status_code == 200
    assert res_factor2.json()["ingredients"] == ["0.2 g saffron", "3 cups water"]


def test_scale_recipe_invalid_factor_zero_and_negative():
    post_res = client.post(
        "/recipes",
        json={"title": "Soup", "ingredients": ["100 g onion"]},
    )
    rid = post_res.json()["id"]

    res_zero = client.get(f"/recipes/{rid}/scaled?factor=0")
    assert res_zero.status_code == 400
    assert res_zero.json()["detail"] == "factor must be a positive number"

    res_neg = client.get(f"/recipes/{rid}/scaled?factor=-2")
    assert res_neg.status_code == 400
    assert res_neg.json()["detail"] == "factor must be a positive number"


def test_scale_recipe_invalid_factor_non_numeric():
    post_res = client.post(
        "/recipes",
        json={"title": "Soup", "ingredients": ["100 g onion"]},
    )
    rid = post_res.json()["id"]

    res_non_num = client.get(f"/recipes/{rid}/scaled?factor=two")
    assert res_non_num.status_code == 422

    res_missing = client.get(f"/recipes/{rid}/scaled")
    assert res_missing.status_code == 422


def test_scale_recipe_unknown_recipe_404():
    res = client.get("/recipes/99999/scaled?factor=2")
    assert res.status_code == 404
    assert res.json()["detail"] == "unknown recipe"


def test_scale_recipe_stored_recipe_not_modified():
    post_res = client.post(
        "/recipes",
        json={"title": "Cookies", "ingredients": ["200 g flour", "100 g sugar", "pinch of salt"]},
    )
    rid = post_res.json()["id"]

    # Call scaled endpoint
    scaled_res = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert scaled_res.status_code == 200
    assert scaled_res.json()["ingredients"] == ["400 g flour", "200 g sugar", "pinch of salt"]

    # Verify original recipe in DB is unmodified
    orig_res = client.get(f"/recipes/{rid}")
    assert orig_res.status_code == 200
    assert orig_res.json()["ingredients"] == ["200 g flour", "100 g sugar", "pinch of salt"]


def test_scale_ingredient_mixed_fraction_and_units():
    from main import scale_ingredient

    assert scale_ingredient("1 1/2 cups flour", 2) == "3 cups flour"
    assert scale_ingredient("2 1/4 cups flour", 2) == "4.5 cups flour"
    assert scale_ingredient("100g sugar", 2) == "200g sugar"
    assert scale_ingredient("  50 ml water", 2) == "  100 ml water"
    assert scale_ingredient("", 2) == ""

