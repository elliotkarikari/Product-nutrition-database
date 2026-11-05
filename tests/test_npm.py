import unittest

from shelfscale.npm import calculate_npm, sodium_mg_from_salt_g


class TestNPM(unittest.TestCase):
    def test_baked_beans_fixture(self):
        # Synthetic fixture with baked-bean-like values. It is NOT one of the
        # guidance's worked examples (those are in test_npm_worked_examples).
        # Expected A = 4, C = 6, score = -2.
        result = calculate_npm(
            energy_kj=340,
            saturated_fat_g=0.1,
            total_sugars_g=5,
            sodium_mg=250,
            fruit_veg_nuts_percent=50,
            fibre_aoac_g=3.7,
            protein_g=4.8,
        )
        self.assertEqual(result.total_a, 4)
        self.assertEqual(result.total_c, 6)
        self.assertEqual(result.score, -2)
        self.assertFalse(result.less_healthy)

    def test_protein_rule_blocks_protein_at_high_a(self):
        result = calculate_npm(
            energy_kj=3400,  # 10 A points
            saturated_fat_g=1.1,  # 1 A point, total A = 11
            total_sugars_g=0,
            sodium_mg=0,
            fruit_veg_nuts_percent=0,
            fibre_aoac_g=5.0,  # 5 C points
            protein_g=9.0,  # would be 5 C points if counted
        )
        self.assertEqual(result.total_a, 11)
        self.assertFalse(result.protein_counted)
        self.assertEqual(result.c_points["protein"], 0)
        self.assertEqual(result.score, 6)
        self.assertTrue(result.less_healthy)

    def test_full_fruit_veg_nut_points_rescue_protein(self):
        result = calculate_npm(
            energy_kj=3400,
            saturated_fat_g=1.1,
            total_sugars_g=0,
            sodium_mg=0,
            fruit_veg_nuts_percent=90,  # 5 C points
            fibre_aoac_g=0,
            protein_g=9.0,  # 5 C points, counted because FVN = 5
        )
        self.assertTrue(result.protein_counted)
        self.assertEqual(result.total_c, 10)
        self.assertEqual(result.score, 1)
        self.assertFalse(result.less_healthy)

    def test_drink_threshold_is_one(self):
        kwargs = dict(
            energy_kj=340,
            saturated_fat_g=0.1,
            total_sugars_g=5,
            sodium_mg=250,
            fruit_veg_nuts_percent=50,
            fibre_aoac_g=3.7,
            protein_g=4.8,
        )
        food = calculate_npm(**kwargs)
        drink = calculate_npm(**kwargs, is_drink=True)
        self.assertEqual(food.score, drink.score)
        # Same score, different legal meaning is covered by the threshold:
        sweet_drink = calculate_npm(
            energy_kj=180,
            saturated_fat_g=0,
            total_sugars_g=10,
            sodium_mg=0,
            fruit_veg_nuts_percent=0,
            fibre_aoac_g=0,
            protein_g=0,
            is_drink=True,
        )
        self.assertEqual(sweet_drink.score, 2)
        self.assertTrue(sweet_drink.less_healthy)

    def test_salt_conversion(self):
        self.assertAlmostEqual(sodium_mg_from_salt_g(0.625), 250.0)
        by_salt = calculate_npm(
            energy_kj=340,
            saturated_fat_g=0.1,
            total_sugars_g=5,
            salt_g=0.625,
            fruit_veg_nuts_percent=50,
            fibre_aoac_g=3.7,
            protein_g=4.8,
        )
        self.assertEqual(by_salt.a_points["sodium"], 2)

    def test_sodium_source_must_be_unambiguous(self):
        with self.assertRaises(ValueError):
            calculate_npm(
                energy_kj=100,
                saturated_fat_g=0,
                total_sugars_g=0,
                fruit_veg_nuts_percent=0,
                fibre_aoac_g=0,
                protein_g=0,
            )
        with self.assertRaises(ValueError):
            calculate_npm(
                energy_kj=100,
                saturated_fat_g=0,
                total_sugars_g=0,
                sodium_mg=10,
                salt_g=0.025,
                fruit_veg_nuts_percent=0,
                fibre_aoac_g=0,
                protein_g=0,
            )


if __name__ == "__main__":
    unittest.main()
