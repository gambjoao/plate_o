# Creates the tag vocabulary (country / region / diet / spice_level) and
# assigns tags to all 84 recipes.
#
# Country/region assignments are my read of each recipe's cultural origin
# from its name and instructions (see the conversation this was built in).
# A recipe gets both its country and region tag where a clear origin exists;
# recipes with no single clear cultural origin (fusion bowls, generic
# sandwiches/steaks) get no country/region tag at all rather than a guess.
#
# Diet tags (Vegetariano/Vegan) are NOT a judgment call: they were derived
# by cross-referencing each recipe's actual MealIngredient rows against the
# nutrition-token data (red_meat/white_meat/fish/seafood/dairy) plus a manual
# list of animal-derived ingredients that were deliberately left un-tokened
# (ovos, mel, manteiga, natas, maionese, maionese kewpie, caldo de frango,
# caldo de vaca, caldo de marisco, po de frango, molho de peixe, molho de
# ostras) since those don't carry a meaningful per-100g token *quantity* but
# their mere presence still disqualifies a dish from being vegetarian/vegan.
# A recipe tagged Vegan is also tagged Vegetariano (vegan is a subset), so
# filtering by "Vegetariano" surfaces vegan recipes too.
#
# Spice level (Picante) is applied only to recipes where a genuinely
# heat-forward chili/gochujang/Sichuan-pepper ingredient is a defining part
# of the dish, not a light garnish (e.g. Pho's optional sliced chili on the
# side does NOT get tagged; Mapo Tofu's dried chilies + doubanjiang do).

from meals.models import Meal, Tag

COUNTRIES = [
    "Portugal", "Itália", "Espanha", "Grécia", "Bélgica", "França",
    "Marrocos", "Líbano", "Turquia", "Iémen", "Índia", "China", "Japão",
    "Coreia do Sul", "Tailândia", "Vietname", "Indonésia", "Malásia",
    "Filipinas", "México", "Estados Unidos", "Brasil", "Argentina",
]
REGIONS = [
    "Sul da Europa", "Europa Ocidental", "Norte de África", "Médio Oriente",
    "Ásia Oriental", "Sul da Ásia", "Sudeste Asiático", "Américas",
]
DIETS = ["Vegetariano", "Vegan"]
SPICE_LEVELS = ["Picante"]

tag_cache = {}
for name in COUNTRIES:
    tag_cache[name] = Tag.objects.get_or_create(name=name, defaults={"category": "country"})[0]
for name in REGIONS:
    tag_cache[name] = Tag.objects.get_or_create(name=name, defaults={"category": "region"})[0]
for name in DIETS:
    tag_cache[name] = Tag.objects.get_or_create(name=name, defaults={"category": "diet"})[0]
for name in SPICE_LEVELS:
    tag_cache[name] = Tag.objects.get_or_create(name=name, defaults={"category": "spice_level"})[0]

# meal_id -> (country_or_None, region_or_None, diet_tags_list, is_picante)
ASSIGNMENTS = {
    1:  ("Itália", "Sul da Europa", [], False),
    2:  ("Estados Unidos", "Américas", [], True),
    3:  ("Portugal", "Sul da Europa", [], False),
    4:  ("Japão", "Ásia Oriental", [], True),
    5:  ("China", "Ásia Oriental", [], True),
    6:  ("Argentina", "Américas", [], False),
    7:  ("Líbano", "Médio Oriente", [], False),
    8:  (None, None, ["Vegetariano"], False),
    9:  ("Japão", "Ásia Oriental", [], False),
    10: ("Turquia", "Médio Oriente", [], False),
    11: ("Marrocos", "Norte de África", ["Vegetariano"], True),
    12: ("Líbano", "Médio Oriente", ["Vegetariano"], False),
    13: ("Líbano", "Médio Oriente", [], False),
    14: ("Portugal", "Sul da Europa", [], True),
    15: ("Itália", "Sul da Europa", [], True),
    16: ("Itália", "Sul da Europa", [], False),
    17: ("Itália", "Sul da Europa", [], True),
    18: ("México", "Américas", ["Vegetariano"], False),
    19: ("China", "Ásia Oriental", [], False),
    20: ("China", "Ásia Oriental", [], False),
    21: ("Indonésia", "Sudeste Asiático", [], False),
    22: ("Indonésia", "Sudeste Asiático", [], False),
    23: (None, None, ["Vegetariano"], False),
    24: ("Turquia", "Médio Oriente", [], False),
    25: ("Índia", "Sul da Ásia", [], False),
    26: ("Índia", "Sul da Ásia", [], True),
    27: ("Japão", "Ásia Oriental", [], False),
    28: ("Estados Unidos", "Américas", [], False),
    29: ("Malásia", "Sudeste Asiático", [], True),
    30: ("Índia", "Sul da Ásia", [], False),
    31: ("Índia", "Sul da Ásia", [], False),
    32: ("Brasil", "Américas", [], False),
    33: ("México", "Américas", [], False),
    34: ("México", "Américas", [], False),
    35: ("Espanha", "Sul da Europa", ["Vegetariano"], False),
    36: ("Espanha", "Sul da Europa", [], True),
    37: ("Portugal", "Sul da Europa", [], False),
    38: ("Itália", "Sul da Europa", ["Vegetariano"], False),
    39: ("Itália", "Sul da Europa", ["Vegetariano"], False),
    40: ("Portugal", "Sul da Europa", [], False),
    41: ("Portugal", "Sul da Europa", [], False),
    42: ("Japão", "Ásia Oriental", [], True),
    43: ("Grécia", "Sul da Europa", [], False),
    44: ("Tailândia", "Sudeste Asiático", [], False),
    45: ("Filipinas", "Sudeste Asiático", [], False),
    46: ("Portugal", "Sul da Europa", [], False),
    47: ("Vietname", "Sudeste Asiático", [], False),
    48: (None, None, [], False),
    49: ("Itália", "Sul da Europa", [], False),
    50: (None, None, [], False),
    51: ("Portugal", "Sul da Europa", [], False),
    52: ("Bélgica", "Europa Ocidental", [], False),
    53: ("Espanha", "Sul da Europa", [], False),
    54: ("França", "Europa Ocidental", [], False),
    55: ("Itália", "Sul da Europa", [], False),
    56: ("Itália", "Sul da Europa", [], False),
    57: ("Itália", "Sul da Europa", [], False),
    58: ("Itália", "Sul da Europa", ["Vegetariano", "Vegan"], False),
    59: ("China", "Ásia Oriental", [], False),
    60: ("China", "Ásia Oriental", [], True),
    61: ("China", "Ásia Oriental", [], False),
    62: ("China", "Ásia Oriental", [], False),
    63: ("Japão", "Ásia Oriental", [], True),
    64: ("Estados Unidos", "Américas", [], False),
    65: ("Estados Unidos", "Américas", [], False),
    66: ("Índia", "Sul da Ásia", [], True),
    67: (None, None, [], False),
    68: ("Itália", "Sul da Europa", [], False),
    69: ("Portugal", "Sul da Europa", [], False),
    70: ("Itália", "Sul da Europa", ["Vegetariano", "Vegan"], False),
    71: ("Portugal", "Sul da Europa", [], False),
    72: ("Portugal", "Sul da Europa", [], False),
    73: ("Portugal", "Sul da Europa", [], False),
    74: ("Estados Unidos", "Américas", [], False),
    75: ("Portugal", "Sul da Europa", [], False),
    76: ("Líbano", "Médio Oriente", [], False),
    77: ("Turquia", "Médio Oriente", [], False),
    78: ("Líbano", "Médio Oriente", ["Vegetariano", "Vegan"], False),
    79: ("Iémen", "Médio Oriente", [], False),
    80: ("Líbano", "Médio Oriente", ["Vegetariano"], False),
    81: ("Líbano", "Médio Oriente", [], False),
    82: ("Itália", "Sul da Europa", ["Vegetariano"], False),
    377: ("México", "Américas", [], True),
    378: ("Coreia do Sul", "Ásia Oriental", [], True),
}

assert len(ASSIGNMENTS) == 84, f"expected 84 recipes, got {len(ASSIGNMENTS)}"

for meal_id, (country, region, diets, picante) in ASSIGNMENTS.items():
    meal = Meal.objects.get(id=meal_id)
    tags = []
    if country:
        tags.append(tag_cache[country])
    if region:
        tags.append(tag_cache[region])
    for d in diets:
        tags.append(tag_cache[d])
    if picante:
        tags.append(tag_cache["Picante"])
    meal.tags.set(tags)

print("Done. Tags created:", Tag.objects.count())
print("Meals with at least one tag:", Meal.objects.filter(tags__isnull=False).distinct().count())
