import unittest

from beam_core import (
    LoadCase,
    PointLoad,
    Properties,
    integrate_deflection,
    max_abs,
    moment_at,
    solve_statics,
)


class BeamCoreTests(unittest.TestCase):
    def test_w12x26_baseline(self):
        load = LoadCase(uniform=1.0, points=())
        statics = solve_statics(20.0, load, "simple")

        self.assertAlmostEqual(statics.left_reaction, 10.0, places=9)
        self.assertAlmostEqual(statics.right_reaction, 10.0, places=9)
        mid_moment = moment_at(20.0, load, "simple", 10.0, statics)
        self.assertAlmostEqual(mid_moment, 50.0, places=9)

        deflections = integrate_deflection(
            20.0,
            load,
            Properties(elastic_modulus=29000.0, inertia=204.0, section_modulus=33.4),
            "simple",
        )
        maximum = max_abs([value for _, value in deflections])[1]
        self.assertAlmostEqual(abs(maximum), 0.609, places=2)


if __name__ == "__main__":
    unittest.main()
