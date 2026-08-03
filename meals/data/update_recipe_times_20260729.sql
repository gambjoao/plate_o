-- Replaces the placeholder Meal.time = 60 (minutes) for every recipe with a
-- real estimate, read from each recipe's own `instructions` JSON.
--
-- Rule applied consistently: exclude PASSIVE waiting the cook isn't doing
-- anything for -- marinating, room-temp tempering before searing, dough
-- proofing/rising, soaking rice/chickpeas/noodles -- since that's not "time
-- to make it" in the sense the field is used for. DOES include active
-- cooking even when unattended (simmering a ragu for 2h, roasting an
-- octopus/eggplant, a stock simmer) since that's genuinely part of making
-- the dish, plus short post-cook rests (5-10 min) which are standard.
--
-- Only touches meals_meal.time for the given id. Does not touch name,
-- description, instructions, ingredients, or any other column/table.

BEGIN;

UPDATE meals_meal SET time = 140 WHERE id = 1;   -- Esparguete à Bolonhesa (2h ragu simmer + prep)
UPDATE meals_meal SET time = 50  WHERE id = 2;   -- Chili com Carne (quick-cook method, ~20-40min simmer)
UPDATE meals_meal SET time = 20  WHERE id = 3;   -- Salada de Atum (boil eggs, chop, mix)
UPDATE meals_meal SET time = 35  WHERE id = 4;   -- Veggie Ramen
UPDATE meals_meal SET time = 35  WHERE id = 5;   -- Mapo Tofu
UPDATE meals_meal SET time = 20  WHERE id = 6;   -- Bife com Chimichurri (excl. 20min temper rest)
UPDATE meals_meal SET time = 25  WHERE id = 7;   -- Bowl de Hummus e Atum
UPDATE meals_meal SET time = 25  WHERE id = 8;   -- Quinoa Bowls
UPDATE meals_meal SET time = 30  WHERE id = 9;   -- Sushi Bowls
UPDATE meals_meal SET time = 50  WHERE id = 10;  -- Alinazik Kebab (35-45min eggplant roast + meat)
UPDATE meals_meal SET time = 30  WHERE id = 11;  -- Shakshuka
UPDATE meals_meal SET time = 30  WHERE id = 12;  -- Falafel Wraps com Tatziki (excl. 18-24h soak + 1h chill)
UPDATE meals_meal SET time = 35  WHERE id = 13;  -- Pita Shawarma (excl. 1h+ marinate)
UPDATE meals_meal SET time = 45  WHERE id = 14;  -- Arroz de Marisco
UPDATE meals_meal SET time = 30  WHERE id = 15;  -- Esparguete Putanesca
UPDATE meals_meal SET time = 25  WHERE id = 16;  -- Esparguete a la Carbonara
UPDATE meals_meal SET time = 35  WHERE id = 17;  -- Esparguete Amatriciana
UPDATE meals_meal SET time = 40  WHERE id = 18;  -- Vegetarian Crunchwraps
UPDATE meals_meal SET time = 45  WHERE id = 19;  -- Chow mein
UPDATE meals_meal SET time = 20  WHERE id = 20;  -- Arroz Frito
UPDATE meals_meal SET time = 25  WHERE id = 21;  -- Nasi Goreng
UPDATE meals_meal SET time = 140 WHERE id = 22;  -- Rendang de Vaca (2h simmer)
UPDATE meals_meal SET time = 30  WHERE id = 23;  -- Hamburgueres de Cogumelos
UPDATE meals_meal SET time = 35  WHERE id = 24;  -- Wraps de Kebabs (meat mix + tzatziki + salad)
UPDATE meals_meal SET time = 35  WHERE id = 25;  -- Caril de Frango Simples
UPDATE meals_meal SET time = 105 WHERE id = 26;  -- Beef Bhuna (1-1.5h simmer)
UPDATE meals_meal SET time = 40  WHERE id = 27;  -- Combo Japonês
UPDATE meals_meal SET time = 25  WHERE id = 28;  -- Tuna Melts
UPDATE meals_meal SET time = 30  WHERE id = 29;  -- Laksa
UPDATE meals_meal SET time = 30  WHERE id = 30;  -- Butter Chicken (excl. 30min marinate)
UPDATE meals_meal SET time = 70  WHERE id = 31;  -- Chicken Biryani (excl. overnight marinate + rice soak)
UPDATE meals_meal SET time = 45  WHERE id = 32;  -- Bóbó de Camarão
UPDATE meals_meal SET time = 20  WHERE id = 33;  -- Fajitas (excl. 20-30min marinate)
UPDATE meals_meal SET time = 35  WHERE id = 34;  -- Burritos
UPDATE meals_meal SET time = 40  WHERE id = 35;  -- Tortilla de Patata
UPDATE meals_meal SET time = 20  WHERE id = 36;  -- Gambas al Ajillo
UPDATE meals_meal SET time = 20  WHERE id = 37;  -- Ameijoas à Bulhão Pato
UPDATE meals_meal SET time = 25  WHERE id = 38;  -- Esparguete al Pesto
UPDATE meals_meal SET time = 35  WHERE id = 39;  -- Pizza Marguerita (excl. 1h proof)
UPDATE meals_meal SET time = 130 WHERE id = 40;  -- Arroz de Polvo (1.5-2h octopus roast + risotto)
UPDATE meals_meal SET time = 35  WHERE id = 41;  -- Açorda de Marisco
UPDATE meals_meal SET time = 30  WHERE id = 42;  -- Three Fishy Pasta
UPDATE meals_meal SET time = 25  WHERE id = 43;  -- Gyros
UPDATE meals_meal SET time = 25  WHERE id = 44;  -- Pad Thai (excl. 20-30min noodle soak)
UPDATE meals_meal SET time = 50  WHERE id = 45;  -- Chicken Adobo (excl. 1h+ marinate)
UPDATE meals_meal SET time = 20  WHERE id = 46;  -- Robalo Grelhado
UPDATE meals_meal SET time = 300 WHERE id = 47;  -- Pho (roast bones + 4h stock simmer)
UPDATE meals_meal SET time = 45  WHERE id = 48;  -- Frango desfiado à LDB
UPDATE meals_meal SET time = 30  WHERE id = 49;  -- Massa de Atum
UPDATE meals_meal SET time = 20  WHERE id = 50;  -- Bife Grelhado (excl. 30-45min temper rest)
UPDATE meals_meal SET time = 20  WHERE id = 51;  -- Lulas Grelhadas
UPDATE meals_meal SET time = 190 WHERE id = 52;  -- Beef Carbonnade (2-3h braise)
UPDATE meals_meal SET time = 65  WHERE id = 53;  -- Paella de Marisco (incl. ~30min fish stock)
UPDATE meals_meal SET time = 20  WHERE id = 54;  -- Bife au Poivre (excl. 10-15min salt rest)
UPDATE meals_meal SET time = 35  WHERE id = 55;  -- Pizza de Atum (excl. 1h proof)
UPDATE meals_meal SET time = 180 WHERE id = 56;  -- Lasanha Bolonhesa (2h ragu + assembly + bake)
UPDATE meals_meal SET time = 20  WHERE id = 57;  -- Esparguete alle Vongole (excl. 2-3h clam purge)
UPDATE meals_meal SET time = 25  WHERE id = 58;  -- Massa com molho de tomate e pimento
UPDATE meals_meal SET time = 20  WHERE id = 59;  -- Frango Agridoce (excl. 10-20min marinate)
UPDATE meals_meal SET time = 25  WHERE id = 60;  -- Dan Dan Noodles
UPDATE meals_meal SET time = 20  WHERE id = 61;  -- Chop Suey (excl. 20-30min marinate)
UPDATE meals_meal SET time = 35  WHERE id = 62;  -- Siu Mai
UPDATE meals_meal SET time = 30  WHERE id = 63;  -- Karagee Don
UPDATE meals_meal SET time = 10  WHERE id = 64;  -- Turkey Club Sandwich (no cooking)
UPDATE meals_meal SET time = 20  WHERE id = 65;  -- Homemade Big Mac (excl. 30min sauce chill)
UPDATE meals_meal SET time = 50  WHERE id = 66;  -- Tikka Masala (excl. 20min-overnight marinate)
UPDATE meals_meal SET time = 10  WHERE id = 67;  -- Sandes de Salmão Fumado (no cooking)
UPDATE meals_meal SET time = 30  WHERE id = 68;  -- Frango à Tuscana
UPDATE meals_meal SET time = 40  WHERE id = 69;  -- Peitos de Frango Compal e Sopa de Cebola (25-40min bake)
UPDATE meals_meal SET time = 20  WHERE id = 70;  -- Gnochi com Marinara
UPDATE meals_meal SET time = 35  WHERE id = 71;  -- Bacalhau Cozido com grão e ovo
UPDATE meals_meal SET time = 45  WHERE id = 72;  -- Bacalhau à Bráz
UPDATE meals_meal SET time = 30  WHERE id = 73;  -- Douradinhos com Arroz de Tomate
UPDATE meals_meal SET time = 30  WHERE id = 74;  -- McFish caseiro
UPDATE meals_meal SET time = 40  WHERE id = 75;  -- Bitoque
UPDATE meals_meal SET time = 25  WHERE id = 76;  -- Arayes
UPDATE meals_meal SET time = 60  WHERE id = 77;  -- Lahmacun (excl. 1h proof; many small pizzas baked in batches)
UPDATE meals_meal SET time = 50  WHERE id = 78;  -- Mujaddara
UPDATE meals_meal SET time = 85  WHERE id = 79;  -- Frango Bukhari (excl. rice soak; whole-chicken braise + broil + rice)
UPDATE meals_meal SET time = 30  WHERE id = 80;  -- Fatteh Eggplant Salad
UPDATE meals_meal SET time = 45  WHERE id = 81;  -- Baba Ghanoush chicken shawarma bowl (excl. 1h+ marinate; 35-45min eggplant roast)
UPDATE meals_meal SET time = 10  WHERE id = 82;  -- Sandes Caprese (no cooking)
UPDATE meals_meal SET time = 30  WHERE id = 377; -- Tacos Gobernador
UPDATE meals_meal SET time = 20  WHERE id = 378; -- Korean Tuna Melts

COMMIT;
