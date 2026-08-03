-- Adds IngredientNutritionToken rows for ingredients that had none, using the
-- existing dose convention already implied by the 104 previously-populated rows:
-- quantity = (100g reference dose) / (this token's typical dose for that food
-- group) applied per 100 base-units (g/ml) of the ingredient, adjusted up for
-- concentrated forms (pastes/powders/dried) and down for diluted/processed ones.
--
-- Does NOT touch meals_ingredient (names/ids/base_unit untouched) or any other
-- table, and does NOT modify any of the 104 already-populated
-- meals_ingredientnutritiontoken rows.
--
-- Token ids: 1=red_meat 2=white_meat 3=fish 4=seafood 5=veggies 6=legumes

BEGIN;

INSERT INTO meals_ingredientnutritiontoken (ingredient_id, token_id, quantity) VALUES
  -- veggies (token_id 5) -- plain vegetables, same convention as existing 1.00 rows
  (210, 5, 1.00), -- bok choi
  (65,  5, 1.00), -- izote (yucca flower bud, used/cooked as a vegetable)

  -- veggies -- concentrated/dehydrated forms of already-tokened vegetables,
  -- same treatment as existing concentrado de tomate (5.50) / chillies secos (4.50)
  (25,  5, 5.00), -- alho em pó (dehydrated garlic powder)
  (26,  5, 6.00), -- cebola em pó (dehydrated onion powder, higher water loss than garlic)
  (120, 5, 4.50), -- chipotle em pó (dried smoked chili powder)
  (164, 5, 4.50), -- kashmiri chilli em pó (dried chili powder)
  (183, 5, 4.50), -- piri piri seco (dried chili, direct match to existing chillies secos)
  (108, 5, 4.00), -- flocos de malagueta (dried chili flakes, bulkier/less concentrated than pure powder)

  -- veggies -- diluted/brined form
  (218, 5, 0.50), -- gengibre de sushi (pickled ginger, diluted in vinegar brine vs. fresh gengibre=1.00)

  -- legumes (token_id 6) -- soy-based, same family as existing miso/doubanjiang (soy pastes)
  (51,  6, 0.80)  -- tofu (coagulated soy milk, mostly water, lighter than a cooked-pulse dose)
;

COMMIT;
