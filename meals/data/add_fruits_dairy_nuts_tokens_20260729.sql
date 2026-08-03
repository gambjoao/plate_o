-- Adds three new NutritionToken categories (fruits, dairy, nuts) and populates
-- IngredientNutritionToken rows for ingredients that genuinely fit one of them.
-- Same quantity convention as before: quantity = value per 100 base-units
-- (g/ml) of the ingredient, where 1.00 means "100g/100ml of this ingredient is
-- exactly one reference dose."
--
-- Reference doses chosen (my call, as asked):
--   fruits: 100g -- kept parallel to the existing veggies convention (a plain
--     whole fruit / fruit pulp = 1.00), scaled down for diluted nectars/juices
--     and up for reduced/concentrated products, same logic already used for
--     concentrado de tomate (5.50) etc.
--   dairy: no single dose fits milk and hard cheese equally, so dose varies by
--     product density, same way meat doses already vary by cut:
--       liquid milk         -> 200ml  (quantity 0.50)
--       yogurt               -> 125g   (quantity 0.80)
--       fresh/spreadable cheese (mozzarella, cream cheese, processed spread) -> 50g (2.00)
--       semi-hard/brined cheese (feta, processed cheese) -> 40g (2.50)
--       hard cheese (cheddar, gouda, firm melting cheese) -> 30g (3.33)
--       very hard/grated aged cheese (parmesan, pecorino) -> 20g (5.00)
--   nuts: 30g -- a small handful, matching the common ~28-30g nut-serving
--     guidance, applied uniformly (no diluted/concentrated nut products found
--     in the un-tokened list).
--
-- Deliberately excluded (considered, not confident enough to guess a value):
--   lima sun dried, sumac (used like a spice/flavor-infusion, not really
--     "eaten" as fruit); manteiga, natas, leite de coco, maionese/maionese
--     kewpie (fat/egg-based, not a dairy serving despite superficial similarity).
--
-- Does NOT touch meals_ingredient or any previously-existing
-- meals_ingredientnutritiontoken row.

BEGIN;

INSERT INTO meals_nutritiontoken (name, description) VALUES
  ('fruits', 'Whole fruit / fruit pulp equivalent, 100g reference dose.'),
  ('dairy', 'Milk/yogurt/cheese equivalent, dose varies by product density.'),
  ('nuts', 'Tree nuts / peanuts / coconut, 30g reference dose.');

-- fruits
INSERT INTO meals_ingredientnutritiontoken (ingredient_id, token_id, quantity) VALUES
  (131, (SELECT id FROM meals_nutritiontoken WHERE name = 'fruits'), 1.00), -- manga (pulp, assumed undiluted)
  (252, (SELECT id FROM meals_nutritiontoken WHERE name = 'fruits'), 1.00), -- romã (fresh arils)
  (248, (SELECT id FROM meals_nutritiontoken WHERE name = 'fruits'), 4.50), -- passas (dried grapes, ~4-5x concentrated vs fresh)
  (244, (SELECT id FROM meals_nutritiontoken WHERE name = 'fruits'), 0.40), -- compal de pessego pequeno (nectar, diluted w/ water+sugar)
  (251, (SELECT id FROM meals_nutritiontoken WHERE name = 'fruits'), 3.00), -- melaço de romã (reduced/concentrated juice)
  (147, (SELECT id FROM meals_nutritiontoken WHERE name = 'fruits'), 2.50), -- polpa de tamarindo (concentrated pulp)
  (124, (SELECT id FROM meals_nutritiontoken WHERE name = 'fruits'), 1.00), -- lima (sumo)
  (59,  (SELECT id FROM meals_nutritiontoken WHERE name = 'fruits'), 1.00)  -- limão (sumo)
;

-- dairy
INSERT INTO meals_ingredientnutritiontoken (ingredient_id, token_id, quantity) VALUES
  (13,  (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 0.50), -- leite (200ml dose)
  (79,  (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 0.80), -- iogurte (125g dose)
  (190, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 2.00), -- mozarela (fresh cheese, 50g dose)
  (256, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 2.00), -- queijo creme (spreadable, 50g dose)
  (231, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 2.00), -- queijo crème (same as above, alt spelling already in DB)
  (77,  (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 2.00), -- queijo vache que ri (spreadable wedge, 50g dose)
  (86,  (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 2.50), -- queijo feta (brined, 40g dose)
  (241, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 2.50), -- queijo fundido (processed, 40g dose)
  (151, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 3.33), -- queijo cheddar (hard, 30g dose)
  (224, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 3.33), -- queijo gouda (hard, 30g dose)
  (122, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 3.33), -- queijo para derreter (firm melting cheese, 30g dose)
  (187, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 5.00), -- parmesão (very hard/aged, 20g dose)
  (116, (SELECT id FROM meals_nutritiontoken WHERE name = 'dairy'), 5.00)  -- pecorino (very hard/aged, 20g dose)
;

-- nuts
INSERT INTO meals_ingredientnutritiontoken (ingredient_id, token_id, quantity) VALUES
  (247, (SELECT id FROM meals_nutritiontoken WHERE name = 'nuts'), 3.33), -- amendoas torradas
  (195, (SELECT id FROM meals_nutritiontoken WHERE name = 'nuts'), 3.33), -- amendoin torrado (peanut; grouped with nuts, not legumes, dietarily)
  (186, (SELECT id FROM meals_nutritiontoken WHERE name = 'nuts'), 3.33), -- pinhão
  (149, (SELECT id FROM meals_nutritiontoken WHERE name = 'nuts'), 3.33)  -- coco ralado (treated with nuts group, same fat-dense/small-dose logic)
;

COMMIT;
