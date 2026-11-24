import unittest
import tempfile
import os
import csv

import app
from tkinter import filedialog, messagebox

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

    def test_csv_export(self):
        root = app.BeamDesignerApp()
        root.withdraw()
        root.update()
        root._latest_export_rows = [(0.0, 10.0, 0.0, 0.0), (10.0, 0.0, 50.0, -0.608515)]
        handle, path = tempfile.mkstemp(suffix=".csv")
        os.close(handle)
        filedialog.asksaveasfilename = lambda **kwargs: path
        messagebox.showinfo = lambda *args, **kwargs: None
        root.export_csv()
        with open(path, "r", encoding="utf-8-sig", newline="") as csv_file:
            rows = list(csv.reader(csv_file))
        root.destroy()
        os.remove(path)
        self.assertEqual(rows[0], ["x (ft)", "V (kip)", "M (kip-ft)", "Deflection (in)"])
        self.assertEqual(rows[1][0], "0.000000")
        self.assertEqual(rows[2][2], "50.000000000")


if __name__ == "__main__":
    unittest.main()
