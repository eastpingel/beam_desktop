"""Tkinter desktop interface for the Beam Designer."""

import csv
import json
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from beam_core import (
    PointLoad,
    Properties,
    get_coordinates,
    integrate_deflection,
    make_load_case,
    moment_at,
    shear_at,
    solve_statics,
)


BEAMS = [
    "W8x10", "W8x18", "W10x12", "W10x22", "W12x14", "W12x26",
    "W14x22", "W16x26", "W18x35", "W21x44",
    "2x4", "2x6", "2x8", "2x10", "2x12", "4x4", "4x6", "4x8", "6x6",
    "LVL - product data required", "Glulam - product data required",
]


class BeamDesignerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Beam Studio - Beam Analysis")
        self.geometry("1280x820")
        self.minsize(980, 650)
        self.configure(bg="#f3f6f7")

        self.support = "simple"
        self.point_rows: list[dict[str, tk.Widget]] = []
        self._latest_export_rows: list[tuple[float, float, float, float]] = []
        self._latest_report: dict | None = None
        self.build_ui()
        self.add_point_load()
        self.remove_point_row(self.point_rows[0])
        self.apply_member_preset()
        self.analyze()

    def build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f6f7")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#ffffff", foreground="#172a35")
        style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"), background="#ffffff")
        style.configure("Title.TLabel", font=("Segoe UI", 28, "bold"), background="#f3f6f7")
        style.configure("Muted.TLabel", foreground="#647783", background="#f3f6f7")
        style.configure("CardMuted.TLabel", foreground="#647783", background="#ffffff")

        top = tk.Frame(self, bg="#ffffff", height=66, highlightthickness=1, highlightbackground="#dce4e8")
        top.pack(fill="x")
        tk.Label(top, text="Beam Studio", bg="#087e83", fg="white", font=("Segoe UI", 12, "bold"),
                 padx=10, pady=8).pack(side="left", padx=(24, 10), pady=12)
        tk.Label(top, text="BEAM ANALYSIS", bg="#ffffff", fg="#647783",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(top, text="Preliminary screening tool", bg="#ffffff", fg="#647783",
                 font=("Segoe UI", 10)).pack(side="right", padx=24)

        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Save", command=self.save_beam)
        file_menu.add_command(label="Open", command=self.open_beam)
        menu.add_cascade(label="File", menu=file_menu)
        self.configure(menu=menu)

        heading = tk.Frame(self, bg="#f3f6f7")
        heading.pack(fill="x", padx=36, pady=(24, 12))
        tk.Label(heading, text="BEAM DESIGNER", fg="#087e83", bg="#f3f6f7",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(heading, text="Beam designer", bg="#f3f6f7", fg="#172a35",
                 font=("Segoe UI", 28, "bold")).pack(anchor="w")

        banner = tk.Frame(self, bg="#eaf5f3", highlightthickness=1, highlightbackground="#d1e8e4")
        banner.pack(fill="x", padx=36, pady=(0, 16))
        tk.Label(banner, text="Example loaded. 20 ft simply supported W12x26 - 1 kip/ft full-span live load - self-weight excluded.",
                 bg="#eaf5f3", fg="#34585c", font=("Segoe UI", 10), padx=14, pady=9).pack(anchor="w")

        workspace = ttk.Frame(self)
        workspace.pack(fill="both", expand=True, padx=36, pady=(0, 24))
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(0, weight=1)

        left = tk.Frame(workspace, bg="#ffffff", highlightthickness=1, highlightbackground="#dce4e8")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        left_scroll = tk.Canvas(left, bg="#ffffff", highlightthickness=0)
        left_scroll.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(left, orient="vertical", command=left_scroll.yview)
        scrollbar.pack(side="right", fill="y")
        left_scroll.configure(yscrollcommand=scrollbar.set)
        controls = tk.Frame(left_scroll, bg="#ffffff")
        left_scroll.create_window((0, 0), window=controls, anchor="nw")
        controls.bind("<Configure>", lambda event: left_scroll.configure(scrollregion=left_scroll.bbox("all")))

        tk.Label(controls, text="Analysis inputs", bg="#ffffff", fg="#172a35",
                 font=("Segoe UI", 13, "bold"), padx=16, pady=14).pack(fill="x")
        tk.Label(controls, text="All loads are downward service loads.", bg="#ffffff", fg="#647783",
                 font=("Segoe UI", 9), padx=16, pady=12).pack(fill="x")

        section = self.control_section(controls, "Beam model")
        tk.Label(section, text="Support condition", bg="#ffffff", fg="#445964",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        support_frame = tk.Frame(section, bg="#f0f4f5")
        support_frame.pack(fill="x", pady=(4, 10))
        self.support_simple = tk.Button(support_frame, text="Simply supported", relief="flat",
                                        bg="#ffffff", fg="#075f65", font=("Segoe UI", 9, "bold"),
                                        command=lambda: self.set_support("simple"))
        self.support_simple.pack(side="left", fill="x", expand=True, padx=3, pady=3)
        self.support_cantilever = tk.Button(support_frame, text="Cantilever", relief="flat",
                                            bg="#f0f4f5", fg="#637680", font=("Segoe UI", 9, "bold"),
                                            command=lambda: self.set_support("cantilever"))
        self.support_cantilever.pack(side="left", fill="x", expand=True, padx=3, pady=3)

        row = tk.Frame(section, bg="#ffffff")
        row.pack(fill="x")
        self.span = self.labeled_entry(row, "Span", "ft", "20")
        self.beam = self.labeled_combo(row, "Beam member", BEAMS, "W12x26")

        self.material = self.labeled_entry(section, "Grade / product", "", "ASTM A992 - assumed for example")

        section = self.control_section(controls, "Service loads")
        uniforms = tk.Frame(section, bg="#ffffff")
        uniforms.pack(fill="x")
        self.live_uniform = self.labeled_entry(uniforms, "Live uniform", "kip/ft", "1")
        self.other_uniform = self.labeled_entry(uniforms, "Other uniform", "kip/ft", "0")
        tk.Label(section, text="Uniform loads act over the full span. Other uniform load is included in total-load checks.",
                 bg="#ffffff", fg="#81919a", font=("Segoe UI", 9), wraplength=300, justify="left").pack(anchor="w", pady=(4, 8))

        self.point_frame = tk.Frame(section, bg="#ffffff")
        self.point_frame.pack(fill="x")
        tk.Button(section, text="+ Add point load", relief="flat", bg="#ffffff", fg="#087e83",
                  activebackground="#ffffff", font=("Segoe UI", 9, "bold"),
                  command=lambda: self.add_point_load()).pack(anchor="w", pady=(6, 8))

        toggle_row = tk.Frame(section, bg="#ffffff")
        toggle_row.pack(fill="x", pady=(4, 2))
        tk.Label(toggle_row, text="Include beam self-weight", bg="#ffffff", fg="#445964",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.self_weight = tk.BooleanVar(value=False)
        tk.Checkbutton(toggle_row, variable=self.self_weight, bg="#ffffff", activebackground="#ffffff",
                       command=self.analyze).pack(side="right")
        tk.Label(toggle_row, text="Added to total load only", bg="#ffffff", fg="#83929a",
                 font=("Segoe UI", 8)).pack(side="right", padx=8)

        section = self.control_section(controls, "Section properties")
        props = tk.Frame(section, bg="#ffffff")
        props.pack(fill="x")
        self.elastic_modulus = self.labeled_entry(props, "E", "ksi", "29000")
        self.inertia = self.labeled_entry(props, "Ix", "in4", "204")
        self.section_modulus = self.labeled_entry(props, "Sx", "in3", "33.4")
        self.weight = self.labeled_entry(props, "Self-weight", "lb/ft", "26")
        self.deflection_limit = self.labeled_entry(section, "Deflection limit", "in", "0.667")
        self.allow_bending = self.labeled_entry(section, "Allowable bending stress", "ksi - optional", "")
        capacities = tk.Frame(section, bg="#ffffff")
        capacities.pack(fill="x")
        self.allow_shear = self.labeled_entry(capacities, "Shear capacity", "kip - optional", "")
        self.allow_bearing = self.labeled_entry(capacities, "Bearing capacity", "kip/support - optional", "")
        tk.Label(section, text="Only W12x26 has prefilled section values. For other members, enter verified properties.",
                 bg="#f6f8f9", fg="#71818a", font=("Segoe UI", 8), wraplength=300,
                 justify="left", padx=8, pady=6).pack(fill="x", pady=(4, 8))
        self.property_source = self.labeled_entry(section, "Property source / edition", "", "AISC Shapes Database v16.0 - verify benchmark values")

        tk.Button(controls, text="Update analysis", bg="#087e83", fg="white", relief="flat",
                  activebackground="#075f65", font=("Segoe UI", 10, "bold"),
                  command=self.analyze).pack(fill="x", padx=16, pady=14, ipady=7)
        tk.Button(controls, text="Export beam table (CSV)", bg="#ffffff", fg="#087e83", relief="solid",
                  borderwidth=1, activebackground="#eaf5f3", font=("Segoe UI", 9, "bold"),
                  command=self.export_csv).pack(fill="x", padx=16, pady=(0, 14), ipady=6)
        tk.Button(controls, text="Save design report (PDF)", bg="#087e83", fg="white", relief="flat",
                  borderwidth=0, activebackground="#075f65", font=("Segoe UI", 9, "bold"),
                  command=self.export_pdf).pack(fill="x", padx=16, pady=(0, 14), ipady=7)
        self.form_error = tk.Label(controls, text="", bg="#fff2f0", fg="#9c3935",
                                   font=("Segoe UI", 9), wraplength=300, justify="left")

        right_outer = tk.Frame(workspace, bg="#f3f6f7")
        right_outer.grid(row=0, column=1, sticky="nsew")
        right_canvas = tk.Canvas(right_outer, bg="#f3f6f7", highlightthickness=0)
        right_canvas.pack(side="left", fill="both", expand=True)
        right_scroll = ttk.Scrollbar(right_outer, orient="vertical", command=right_canvas.yview)
        right_scroll.pack(side="right", fill="y")
        right_canvas.configure(yscrollcommand=right_scroll.set)
        self.results = tk.Frame(right_canvas, bg="#f3f6f7")
        right_canvas.create_window((0, 0), window=self.results, anchor="nw")
        self.results.bind("<Configure>", lambda event: right_canvas.configure(scrollregion=right_canvas.bbox("all")))

        self.summary_card = self.card("Analysis summary")
        self.summary_subtitle = tk.Label(self.summary_card, text="", bg="#ffffff", fg="#647783", font=("Segoe UI", 9))
        self.summary_subtitle.pack(anchor="w", padx=14)
        self.metrics_frame = tk.Frame(self.summary_card, bg="#ffffff")
        self.metrics_frame.pack(fill="x", padx=10, pady=10)
        self.metric_labels = {}
        for index, name in enumerate(("Support reaction", "Max shear", "Max moment", "Max deflection")):
            box = tk.Frame(self.metrics_frame, bg="#fbfcfc", highlightthickness=1, highlightbackground="#e5ebee")
            box.grid(row=0, column=index, sticky="nsew", padx=4)
            self.metrics_frame.columnconfigure(index, weight=1)
            tk.Label(box, text=name, bg="#fbfcfc", fg="#70818a", font=("Segoe UI", 8, "bold")).pack(padx=8, pady=(8, 2), anchor="w")
            value = tk.Label(box, text="-", bg="#fbfcfc", fg="#203843", font=("Segoe UI", 16, "bold"))
            value.pack(padx=8, pady=(2, 8), anchor="w")
            self.metric_labels[name] = value

        self.beam_card = self.card("Beam and loading")
        self.beam_caption = tk.Label(self.beam_card, text="", bg="#ffffff", fg="#647783", font=("Segoe UI", 9))
        self.beam_caption.pack(anchor="w", padx=14)
        self.beam_canvas = tk.Canvas(self.beam_card, height=170, bg="white", highlightthickness=0)
        self.beam_canvas.pack(fill="x", padx=8, pady=8)

        self.chart_canvases = {}
        for title in ("Shear force", "Bending moment", "Deflection"):
            card = self.card(title)
            canvas = tk.Canvas(card, height=145, bg="white", highlightthickness=0)
            canvas.pack(fill="x", padx=8, pady=8)
            self.chart_canvases[title] = canvas

        self.check_card = self.card("Screening checks")
        self.check_frame = tk.Frame(self.check_card, bg="#ffffff")
        self.check_frame.pack(fill="x", padx=10, pady=10)

        notice = tk.Frame(self.results, bg="#fff9ec", highlightthickness=1, highlightbackground="#eadcbe")
        notice.pack(fill="x", pady=(0, 8))
        tk.Label(notice, text="Preliminary screening only. This tool uses elastic beam theory and user-entered properties. "
                 "It does not evaluate buckling, connections, load combinations, or every applicable design limit state.",
                 bg="#fff9ec", fg="#705b34", font=("Segoe UI", 9), wraplength=760, justify="left",
                 padx=12, pady=10).pack(anchor="w")
        tk.Label(self.results, text="Length in ft - force in kip - section properties in in-based units",
                 bg="#f3f6f7", fg="#8a989f", font=("Segoe UI", 8)).pack(pady=(2, 10))

    def control_section(self, parent, title):
        frame = tk.Frame(parent, bg="#ffffff", highlightthickness=1, highlightbackground="#edf1f3")
        frame.pack(fill="x", padx=10, pady=(0, 8), ipadx=6, ipady=6)
        tk.Label(frame, text=title.upper(), bg="#ffffff", fg="#526671",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(6, 8))
        return frame

    def labeled_entry(self, parent, label, unit, value):
        frame = tk.Frame(parent, bg="#ffffff")
        frame.pack(side="left", fill="x", expand=True, padx=(6, 6), pady=4)
        tk.Label(frame, text=f"{label}  {unit}".strip(), bg="#ffffff", fg="#445964",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        entry = tk.Entry(frame, relief="solid", borderwidth=1, font=("Segoe UI", 9), bg="white")
        entry.insert(0, value)
        entry.pack(fill="x", pady=(3, 0), ipady=4)
        entry.bind("<KeyRelease>", lambda event: self.after_idle(self.analyze))
        return entry

    def labeled_combo(self, parent, label, values, value):
        frame = tk.Frame(parent, bg="#ffffff")
        frame.pack(side="left", fill="x", expand=True, padx=(6, 6), pady=4)
        tk.Label(frame, text=label, bg="#ffffff", fg="#445964",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        combo = ttk.Combobox(frame, values=values, state="readonly", font=("Segoe UI", 9))
        combo.set(value)
        combo.pack(fill="x", pady=(3, 0), ipady=2)
        combo.bind("<<ComboboxSelected>>", lambda event: self.apply_member_preset())
        return combo

    def card(self, title):
        frame = tk.Frame(self.results, bg="#ffffff", highlightthickness=1, highlightbackground="#dce4e8")
        frame.pack(fill="x", pady=(0, 10))
        tk.Label(frame, text=title, bg="#ffffff", fg="#172a35",
                 font=("Segoe UI", 11, "bold"), anchor="w").pack(anchor="w", padx=14, pady=(10, 2))
        return frame

    def set_support(self, support):
        self.support = support
        self.support_simple.configure(bg="#ffffff" if support == "simple" else "#f0f4f5",
                                      fg="#075f65" if support == "simple" else "#637680")
        self.support_cantilever.configure(bg="#ffffff" if support == "cantilever" else "#f0f4f5",
                                          fg="#075f65" if support == "cantilever" else "#637680")
        self.analyze()

    def add_point_load(self):
        row = tk.Frame(self.point_frame, bg="#ffffff")
        row.pack(fill="x", pady=2)
        magnitude = tk.Entry(row, width=9)
        magnitude.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=3)
        magnitude.bind("<KeyRelease>", lambda event: self.after_idle(self.analyze))
        position = tk.Entry(row, width=9)
        position.pack(side="left", fill="x", expand=True, padx=4, ipady=3)
        position.bind("<KeyRelease>", lambda event: self.after_idle(self.analyze))
        kind = ttk.Combobox(row, values=("live", "other"), width=8, state="readonly")
        kind.set("live")
        kind.pack(side="left", padx=4)
        kind.bind("<<ComboboxSelected>>", lambda event: self.analyze())
        remove = tk.Button(row, text="x", width=2, relief="flat", bg="#ffffff", fg="#81919a")
        remove.pack(side="left")
        item = {"row": row, "magnitude": magnitude, "position": position, "kind": kind}
        remove.configure(command=lambda: self.remove_point_row(item))
        self.point_rows.append(item)

    def remove_point_row(self, item):
        if item not in self.point_rows:
            return
        item["row"].destroy()
        self.point_rows.remove(item)
        self.analyze()

    def entry_float(self, entry, default=0.0):
        try:
            return float(entry.get())
        except (TypeError, ValueError):
            return default

    def set_entry(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, "" if value is None else str(value))

    def save_beam(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save beam",
            defaultextension=".json",
            filetypes=[("Beam JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        point_loads = []
        for row in self.point_rows:
            magnitude = row["magnitude"].get().strip()
            position = row["position"].get().strip()
            if magnitude or position:
                point_loads.append({
                    "magnitude": magnitude,
                    "position": position,
                    "kind": row["kind"].get(),
                })

        beam = {
            "format": "beam-studio",
            "version": 1,
            "support": self.support,
            "span_ft": self.span.get(),
            "section": self.beam.get(),
            "deflection_limit_in": self.deflection_limit.get(),
            "material": self.material.get(),
            "property_source": self.property_source.get(),
            "loads": {
                "live_uniform_kip_ft": self.live_uniform.get(),
                "other_uniform_kip_ft": self.other_uniform.get(),
                "point_loads": point_loads,
                "include_self_weight": self.self_weight.get(),
            },
            "section_properties": {
                "elastic_modulus_ksi": self.elastic_modulus.get(),
                "inertia_in4": self.inertia.get(),
                "section_modulus_in3": self.section_modulus.get(),
                "self_weight_lb_ft": self.weight.get(),
                "allowable_bending_ksi": self.allow_bending.get(),
                "allowable_shear_kip": self.allow_shear.get(),
                "allowable_bearing_kip": self.allow_bearing.get(),
            },
        }

        try:
            with open(path, "w", encoding="utf-8") as beam_file:
                json.dump(beam, beam_file, indent=2)
        except OSError as error:
            messagebox.showerror("Save failed", str(error), parent=self)
            return
        messagebox.showinfo("Beam saved", f"Saved beam to:\n{path}", parent=self)

    def open_beam(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Open beam",
            filetypes=[("Beam JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as beam_file:
                beam = json.load(beam_file)
        except (OSError, json.JSONDecodeError) as error:
            messagebox.showerror("Open failed", str(error), parent=self)
            return

        if beam.get("format") != "beam-studio":
            messagebox.showerror("Open failed", "The selected file is not a Beam Studio beam file.", parent=self)
            return

        support = beam.get("support")
        if support not in ("simple", "cantilever"):
            messagebox.showerror("Open failed", "The beam file has an invalid support type.", parent=self)
            return
        self.set_support(support)

        self.set_entry(self.span, beam.get("span_ft", ""))
        section_name = beam.get("section", "")
        if section_name in BEAMS:
            self.beam.set(section_name)
        else:
            messagebox.showerror("Open failed", "The beam file has an unknown section.", parent=self)
            return
        self.set_entry(self.deflection_limit, beam.get("deflection_limit_in", ""))
        self.set_entry(self.material, beam.get("material", ""))
        self.set_entry(self.property_source, beam.get("property_source", ""))

        loads = beam.get("loads", {})
        self.set_entry(self.live_uniform, loads.get("live_uniform_kip_ft", ""))
        self.set_entry(self.other_uniform, loads.get("other_uniform_kip_ft", ""))
        self.self_weight.set(bool(loads.get("include_self_weight", False)))

        properties = beam.get("section_properties", {})
        property_entries = (
            (self.elastic_modulus, "elastic_modulus_ksi"),
            (self.inertia, "inertia_in4"),
            (self.section_modulus, "section_modulus_in3"),
            (self.weight, "self_weight_lb_ft"),
            (self.allow_bending, "allowable_bending_ksi"),
            (self.allow_shear, "allowable_shear_kip"),
            (self.allow_bearing, "allowable_bearing_kip"),
        )
        for entry, key in property_entries:
            self.set_entry(entry, properties.get(key, ""))

        for item in list(self.point_rows):
            item["row"].destroy()
            self.point_rows.remove(item)
        for point in loads.get("point_loads", []):
            self.add_point_load()
            item = self.point_rows[-1]
            self.set_entry(item["magnitude"], point.get("magnitude", ""))
            self.set_entry(item["position"], point.get("position", ""))
            kind = point.get("kind", "live")
            item["kind"].set(kind if kind in ("live", "other") else "live")
        if not self.point_rows:
            self.add_point_load()
            self.remove_point_row(self.point_rows[0])

        self.analyze()
        messagebox.showinfo("Beam opened", f"Opened beam from:\n{path}", parent=self)

    def apply_member_preset(self):
        if self.beam.get() == "W12x26":
            values = ("29000", "204", "33.4", "26", "ASTM A992 - assumed for example",
                      "AISC Shapes Database v16.0 - verify benchmark values")
        else:
            values = ("", "", "", "", "", "")
        if self.beam.get() == "W12x26" and self.deflection_limit.get() == "":
            self.set_entry(self.deflection_limit, "0.667")
        for entry, value in zip(
            (self.elastic_modulus, self.inertia, self.section_modulus, self.weight,
             self.material, self.property_source),
            values,
        ):
            entry.delete(0, "end")
            entry.insert(0, value)
        self.analyze()

    def read_point_loads(self):
        loads = []
        for row in self.point_rows:
            mag_text = row["magnitude"].get().strip()
            pos_text = row["position"].get().strip()
            if not mag_text and not pos_text:
                continue
            try:
                loads.append(PointLoad(float(mag_text), float(pos_text), row["kind"].get()))
            except ValueError:
                loads.append(PointLoad(float("nan"), float("nan"), row["kind"].get()))
        return loads

    def analyze(self):
        try:
            span = float(self.span.get())
            live_uniform = float(self.live_uniform.get() or 0)
            other_uniform = float(self.other_uniform.get() or 0)
        except ValueError:
            self.show_error("Enter a valid span and uniform loads.")
            return

        point_loads = self.read_point_loads()
        properties = Properties(
            elastic_modulus=self.entry_float(self.elastic_modulus),
            inertia=self.entry_float(self.inertia),
            section_modulus=self.entry_float(self.section_modulus),
            weight=self.entry_float(self.weight),
        )
        try:
            deflection_limit = float(self.deflection_limit.get())
        except ValueError:
            deflection_limit = 0.0
        errors = []
        if span <= 0 or span > 500:
            errors.append("Enter a span greater than 0 and no more than 500 ft.")
        if deflection_limit <= 0:
            errors.append("Enter a positive deflection limit in inches.")
        if live_uniform < 0 or other_uniform < 0:
            errors.append("Uniform loads must be zero or greater.")
        for index, point in enumerate(point_loads, 1):
            if point.magnitude < 0:
                errors.append(f"Point load {index} must have a nonnegative magnitude.")
            if point.position < 0 or point.position > span:
                errors.append(f"Point load {index} must be positioned between 0 and the span.")
        if self.self_weight.get() and properties.weight < 0:
            errors.append("Enter a valid self-weight or turn off automatic self-weight.")
        if properties.elastic_modulus < 0 or properties.inertia < 0 or properties.section_modulus < 0:
            errors.append("Section properties must be zero or greater.")
        if errors:
            self.show_error(errors[0])
            return
        self.form_error.pack_forget()

        total_case = make_load_case(live_uniform, other_uniform, point_loads, "total",
                                    self.self_weight.get(), properties.weight)
        live_case = make_load_case(live_uniform, other_uniform, point_loads, "live")
        total_statics = solve_statics(span, total_case, self.support)
        coordinates = get_coordinates(span, total_case.points)
        live_coordinates = get_coordinates(span, live_case.points)
        total_points = [(x, shear_at(span, total_case, self.support, x, total_statics),
                         moment_at(span, total_case, self.support, x, total_statics)) for x in coordinates]
        live_deflection = integrate_deflection(span, live_case, properties, self.support, live_coordinates)
        total_deflection = integrate_deflection(span, total_case, properties, self.support, coordinates)
        deflection_by_x = {round(x_ft, 9): deflection for x_ft, deflection in total_deflection}
        self._latest_export_rows = [
            (x_ft, shear, moment, deflection_by_x.get(round(x_ft, 9), 0.0))
            for x_ft, shear, moment in total_points
        ]

        max_shear_index = max(range(len(total_points)), key=lambda i: abs(total_points[i][1]))
        max_moment_index = max(range(len(total_points)), key=lambda i: abs(total_points[i][2]))
        peak_shear = total_points[max_shear_index]
        peak_moment = total_points[max_moment_index]
        peak_deflection = max(total_deflection, key=lambda item: abs(item[1]), default=(0.0, 0.0))

        reaction_text = f"{total_statics.left_reaction:.2f} kip"
        if self.support == "simple":
            reaction_text = f"{total_statics.left_reaction:.2f} / {total_statics.right_reaction:.2f} kip"
        self.metric_labels["Support reaction"].configure(text=reaction_text)
        self.metric_labels["Max shear"].configure(text=f"{abs(peak_shear[1]):.2f} kip")
        self.metric_labels["Max moment"].configure(text=f"{abs(peak_moment[2]):.2f} kip-ft")
        self.metric_labels["Max deflection"].configure(text=f"{abs(peak_deflection[1]):.3f} in")
        support_name = "Simply supported" if self.support == "simple" else "Cantilever"
        self.summary_subtitle.configure(text=f"{support_name} - {span:.2f} ft span - {self.beam.get()}")
        self.beam_caption.configure(text=f"{self.beam.get()} - {self.material.get() or 'Material not specified'} - {span:.2f} ft")

        self.draw_beam(span, total_case, total_statics)
        self.draw_chart("Shear force", [(x, v) for x, _, v in []], "kip")
        self.draw_chart("Shear force", [(x, shear) for x, shear, _ in total_points], "kip")
        self.draw_chart("Bending moment", [(x, moment) for x, _, moment in total_points], "kip-ft")
        self.draw_chart("Deflection", total_deflection, "in", deflection_limit)
        self.draw_checks(span, deflection_limit, total_points, total_deflection, live_deflection, properties)
        point_load_data = [
            (point.magnitude, point.position, point.kind)
            for point in point_loads
        ]
        check_data = self.get_check_report(
            span, deflection_limit, total_points, total_deflection,
            live_deflection, properties,
        )
        self._latest_report = {
            "support": "Simply supported" if self.support == "simple" else "Cantilever",
            "span": span,
            "section": self.beam.get(),
            "material": self.material.get(),
            "live_uniform": live_uniform,
            "other_uniform": other_uniform,
            "point_loads": point_load_data,
            "include_self_weight": self.self_weight.get(),
            "elastic_modulus": properties.elastic_modulus,
            "inertia": properties.inertia,
            "section_modulus": properties.section_modulus,
            "self_weight": properties.weight,
            "property_source": self.property_source.get(),
            "deflection_limit": deflection_limit,
            "left_reaction": total_statics.left_reaction,
            "right_reaction": total_statics.right_reaction,
            "max_shear": abs(peak_shear[1]),
            "max_moment": abs(peak_moment[2]),
            "max_deflection": abs(peak_deflection[1]),
            "checks": check_data,
            "beam_loading": total_points,
            "deflection": total_deflection,
        }

    def show_error(self, message):
        self.form_error.configure(text=message)
        self.form_error.pack(fill="x", padx=16, pady=(0, 10))

    def export_csv(self):
        if not self._latest_export_rows:
            messagebox.showerror(
                "Export unavailable",
                "Run a valid analysis before exporting the beam table.",
                parent=self,
            )
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export beam table",
            defaultextension=".csv",
            filetypes=[("Excel CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["x (ft)", "V (kip)", "M (kip-ft)", "Deflection (in)"])
                for x_ft, shear, moment, deflection in self._latest_export_rows:
                    writer.writerow([
                        f"{x_ft:.6f}",
                        f"{shear:.9f}",
                        f"{moment:.9f}",
                        f"{deflection:.9f}",
                    ])
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self)
            return
        messagebox.showinfo("Beam table exported", f"Exported CSV to:\n{path}", parent=self)

    def get_check_report(self, span, deflection_limit, total_points,
                         total_deflection, live_deflection, properties):
        max_shear = max(abs(point[1]) for point in total_points)
        max_moment = max(abs(point[2]) for point in total_points)
        max_deflection = max((abs(value) for _, value in total_deflection), default=0)
        max_live_deflection = max((abs(value) for _, value in live_deflection), default=0)
        bending_stress = (
            max_moment * 12 / properties.section_modulus
            if properties.section_modulus > 0 else 0
        )
        try:
            bending_limit = float(self.allow_bending.get())
        except ValueError:
            bending_limit = 0
        try:
            shear_limit = float(self.allow_shear.get())
        except ValueError:
            shear_limit = 0
        try:
            bearing_limit = float(self.allow_bearing.get())
        except ValueError:
            bearing_limit = 0
        max_bearing = abs(solve_statics(
            span,
            make_load_case(
                self.entry_float(self.live_uniform),
                self.entry_float(self.other_uniform),
                self.read_point_loads(),
                "total",
                self.self_weight.get(),
                properties.weight,
            ),
            self.support,
        ).left_reaction)
        checks = [
            ("Bending stress", bending_stress, bending_limit, "ksi",
             "fb = M/Sx"),
            ("Total-load deflection", max_deflection, deflection_limit, "in",
             "Entered limit"),
            ("Live-load deflection", max_live_deflection, deflection_limit, "in",
             "Entered limit"),
            ("Shear strength", max_shear, shear_limit, "kip",
             "Entered capacity"),
            ("Support bearing", max_bearing, bearing_limit, "kip/support",
             "Maximum reaction"),
        ]
        result = []
        for name, value, limit_value, unit, detail in checks:
            status = "Not checked"
            if name in ("Bending stress", "Shear strength", "Support bearing") and limit_value > 0:
                status = "Pass" if value <= limit_value else "Fail"
            elif name in ("Total-load deflection", "Live-load deflection"):
                status = "Pass" if value <= limit_value else "Fail"
            result.append({
                "name": name,
                "value": value,
                "limit": limit_value,
                "unit": unit,
                "detail": detail,
                "status": status,
            })
        return result

    @staticmethod
    def pdf_escape(value):
        return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def export_pdf(self):
        if not self._latest_report:
            messagebox.showerror(
                "Export unavailable",
                "Run a valid analysis before exporting the PDF report.",
                parent=self,
            )
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save design report",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return

        report = self._latest_report
        commands = []

        def text(x, y, size, value):
            commands.append(
                f"BT /F1 {size} Tf {x:.1f} {y:.1f} Td "
                f"({self.pdf_escape(value)}) Tj ET"
            )

        def line(x1, y1, x2, y2, width=1):
            commands.append(
                f"{width:.1f} w {x1:.1f} {y1:.1f} m "
                f"{x2:.1f} {y2:.1f} l S"
            )

        text(36, 752, 18, "Beam Studio - Design Screening Report")
        text(36, 732, 9, f"Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        text(36, 704, 12, "Inputs")
        y = 684
        input_lines = [
            f"Support: {report['support']}",
            f"Span: {report['span']:.2f} ft",
            f"Section: {report['section']} | Material: {report['material'] or 'Not specified'}",
            f"Live uniform: {report['live_uniform']:.3f} kip/ft",
            f"Other uniform: {report['other_uniform']:.3f} kip/ft",
            f"Self-weight included: {'Yes' if report['include_self_weight'] else 'No'} "
            f"({report['self_weight']:.2f} lb/ft)",
            f"E: {report['elastic_modulus']:.2f} ksi | "
            f"Ix: {report['inertia']:.2f} in4 | "
            f"Sx: {report['section_modulus']:.2f} in3",
            f"Deflection limit: {report['deflection_limit']:.3f} in",
            f"Property source: {report['property_source'] or 'Not specified'}",
        ]
        if report["point_loads"]:
            input_lines.append(
                "Point loads: "
                + "; ".join(
                    f"{magnitude:.3f} kip at {position:.2f} ft ({kind})"
                    for magnitude, position, kind in report["point_loads"]
                )
            )
        else:
            input_lines.append("Point loads: None")
        for input_line in input_lines:
            text(36, y, 8, input_line)
            y -= 16

        def draw_plot(title, unit, values, x_min, y_top, x_max, y_bottom, limit=None):
            text(x_min, y_top + 18, 10, title)
            line(x_min, y_bottom, x_max, y_bottom)
            line(x_min, y_bottom, x_min, y_top)
            if not values:
                return
            xs = [point[0] for point in values]
            ys = [point[1] for point in values]
            span = max(report["span"], 0.0001)
            max_abs = max([abs(value) for value in ys] or [0.0001])
            previous = None
            for x_ft, value in values:
                px = x_min + (x_max - x_min) * x_ft / span
                py = (y_top + y_bottom) / 2 - (y_bottom - y_top) / 2 * value / (max_abs * 1.1)
                if previous:
                    line(previous[0], previous[1], px, py)
                previous = (px, py)
            if limit is not None:
                py = (y_top + y_bottom) / 2 - (y_bottom - y_top) / 2 * limit / (max_abs * 1.1)
                line(x_min, py, x_max, py)
                text(x_max - 100, py + 4, 7, f"Limit {limit:.3f} {unit}")
            text(x_min, y_bottom - 12, 7, f"0 ft")
            text(x_max - 25, y_bottom - 12, 7, f"{span:.1f} ft")

        beam_loading = [
            (x_ft, shear)
            for x_ft, shear, _ in report["beam_loading"]
        ]
        moment_loading = [
            (x_ft, moment)
            for x_ft, _, moment in report["beam_loading"]
        ]
        deflection_loading = report["deflection"]

        draw_plot("Shear force (kip)", "kip", beam_loading, 36, 470, 576, 390)
        draw_plot("Bending moment (kip-ft)", "kip-ft", moment_loading, 36, 340, 576, 260)
        draw_plot(
            "Deflection (in)",
            "in",
            deflection_loading,
            36,
            210,
            576,
            130,
            report["deflection_limit"],
        )
        text(36, 102, 8,
             f"Reactions: left {report['left_reaction']:.2f} kip")
        text(36, 88, 8,
             f"Maximum shear: {report['max_shear']:.2f} kip | "
             f"Maximum moment: {report['max_moment']:.2f} kip-ft | "
             f"Maximum deflection: {report['max_deflection']:.3f} in")

        page1_commands = commands

        check_commands = []
        def check_text(x, y, size, value):
            check_commands.append(
                f"BT /F1 {size} Tf {x:.1f} {y:.1f} Td "
                f"({self.pdf_escape(value)}) Tj ET"
            )
        check_text(36, 752, 18, "Beam Studio - Screening Checks")
        check_text(36, 728, 9, f"Section: {report['section']} | Span: {report['span']:.2f} ft")
        y = 694
        for check in report["checks"]:
            limit_text = (
                f" | Limit: {check['limit']:.3f} {check['unit']}"
                if check["limit"] > 0 else " | Limit: Not entered"
            )
            check_text(
                36,
                y,
                10,
                f"{check['name']}: {check['status']} - "
                f"{check['value']:.3f} {check['unit']}{limit_text}",
            )
            check_text(36, y - 13, 8, f"Basis: {check['detail']}")
            y -= 42
        check_text(36, 430, 9, "Not evaluated")
        check_text(
            36,
            414,
            8,
            "Buckling, connections, load combinations, and every applicable unimplemented limit state.",
        )
        check_text(
            36,
            392,
            8,
            "Preliminary screening only. Verify member properties and assumptions with a qualified structural professional.",
        )

        self.write_pdf(path, page1_commands, check_commands)
        messagebox.showinfo("PDF report saved", f"Saved design report to:\n{path}", parent=self)

    def write_pdf(self, path, page1_commands, page2_commands):
        stream1 = "\n".join(page1_commands).encode("latin-1", "replace")
        stream2 = "\n".join(page2_commands).encode("latin-1", "replace")

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [4 0 R 6 0 R] /Count 2 >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
            b"<< /Length " + str(len(stream1)).encode("ascii") + b" >>\nstream\n"
            + stream1 + b"\nendstream",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents 7 0 R >>",
            b"<< /Length " + str(len(stream2)).encode("ascii") + b" >>\nstream\n"
            + stream2 + b"\nendstream",
        ]

        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for object_number, body in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
            pdf.extend(body)
            pdf.extend(b"\nendobj\n")

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )
        with open(path, "wb") as pdf_file:
            pdf_file.write(pdf)

    def draw_beam(self, span, load_case, statics):
        canvas = self.beam_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 700)
        height = 170
        left, right, y = 70, width - 70, 78
        canvas.create_line(left, y, right, y, fill="#087e83", width=8)
        if self.support == "simple":
            canvas.create_polygon(left - 14, y + 16, left + 14, y + 16, left, y + 5,
                                  fill="#e9eef0", outline="#71838d")
            canvas.create_polygon(right - 14, y + 16, right + 14, y + 16, right, y + 5,
                                  fill="#e9eef0", outline="#71838d")
        else:
            canvas.create_line(left - 12, y - 25, left - 12, y + 25, fill="#71838d", width=3)
            canvas.create_line(left - 7, y - 25, left - 7, y + 25, fill="#71838d", width=1)
        if load_case.uniform > 0:
            for index in range(16):
                x = left + (right - left) * index / 15
                canvas.create_line(x, 31, x, 66, fill="#d59d39", arrow="last", width=1)
        for point in load_case.points:
            x = left + (right - left) * point.position / span
            canvas.create_line(x, 42, x, y - 4, fill="#d59d39", arrow="last", width=2)
            canvas.create_text(x, 28, text=f"{point.magnitude:.2f} kip", fill="#9b7028", font=("Segoe UI", 8))
        canvas.create_text((left + right) / 2, 145, text=f"Span - {span:.2f} ft",
                           fill="#71818a", font=("Segoe UI", 9))
        if self.support == "simple":
            canvas.create_text(left, 160, text=f"R = {statics.left_reaction:.2f} kip",
                               fill="#71818a", font=("Segoe UI", 8))
            canvas.create_text(right, 160, text=f"R = {statics.right_reaction:.2f} kip",
                               fill="#71818a", font=("Segoe UI", 8))

    def draw_chart(self, title, points, unit, limit=None):
        canvas = self.chart_canvases[title]
        canvas.delete("all")
        width = max(canvas.winfo_width(), 700)
        height = 145
        left, right, top, bottom = 50, width - 30, 15, 112
        span = float(self.span.get())
        if not points:
            canvas.create_text(width / 2, height / 2, text="No data", fill="#91a0a7")
            return
        values = [value for _, value in points]
        max_abs = max([abs(value) for value in values] or [0.0001])
        scale = max_abs * 1.2
        is_deflection = title == "Deflection"
        mid = 18 if is_deflection else (top + bottom) / 2
        canvas.create_line(left, mid, right, mid, fill="#b7c3c8")
        coordinates = []
        for x, value in points:
            px = left + (right - left) * x / span
            py = (top + (bottom - top) * value / scale) if is_deflection else mid - (bottom - top) / 2 * value / scale
            coordinates.extend((px, py))
        if len(coordinates) >= 4:
            canvas.create_line(coordinates, fill="#087e83", width=2, smooth=True)
            if is_deflection:
                canvas.create_polygon(*coordinates, right, mid, left, mid, fill="#087e83", stipple="gray25", outline="")
        for fraction in (0, 0.25, 0.5, 0.75, 1):
            x = left + (right - left) * fraction
            canvas.create_line(x, top, x, bottom, fill="#eef2f3")
            canvas.create_text(x, 132, text=f"{span * fraction:.1f}", fill="#84939b", font=("Segoe UI", 8))
        if limit is not None:
            py = top + (bottom - top) * limit / scale
            canvas.create_line(left, py, right, py, fill="#d59d39", dash=(5, 4))
            canvas.create_text(right, py - 5, text=f"L/360 - {limit:.3f} {unit}", fill="#9b7028",
                               font=("Segoe UI", 8), anchor="e")

    def draw_checks(self, span, deflection_limit, total_points, total_deflection, live_deflection, properties):
        for widget in self.check_frame.winfo_children():
            widget.destroy()
        max_shear = max(abs(point[1]) for point in total_points)
        max_moment = max(abs(point[2]) for point in total_points)
        bending_stress = max_moment * 12 / properties.section_modulus if properties.section_modulus > 0 else 0
        max_deflection = max((abs(value) for _, value in total_deflection), default=0)
        max_live_deflection = max((abs(value) for _, value in live_deflection), default=0)
        checks = []
        try:
            bending_limit = float(self.allow_bending.get())
        except ValueError:
            bending_limit = 0
        try:
            shear_limit = float(self.allow_shear.get())
        except ValueError:
            shear_limit = 0
        try:
            bearing_limit = float(self.allow_bearing.get())
        except ValueError:
            bearing_limit = 0
        checks.append(("Bending stress", bending_stress, bending_limit, "ksi", "fb = M/Sx"))
        checks.append(("Total-load deflection", max_deflection, deflection_limit, "in", "Entered limit"))
        checks.append(("Live-load deflection", max_live_deflection, deflection_limit, "in", "Entered limit"))
        checks.append(("Shear strength", max_shear, shear_limit, "kip", "Entered capacity"))
        max_bearing = abs(solve_statics(span, make_load_case(
            self.entry_float(self.live_uniform),
            self.entry_float(self.other_uniform),
            self.read_point_loads(),
            "total",
            self.self_weight.get(),
            properties.weight,
        ), self.support).left_reaction)
        checks.append(("Support bearing", max_bearing, bearing_limit, "kip/support", "Maximum reaction"))

        for index, (name, value, limit_value, unit, detail) in enumerate(checks):
            box = tk.Frame(self.check_frame, bg="#fbfcfc", highlightthickness=1, highlightbackground="#e5ebee")
            box.grid(row=index // 2, column=index % 2, sticky="nsew", padx=5, pady=5)
            self.check_frame.columnconfigure(index % 2, weight=1)
            status = "Not checked"
            status_color = "#74848c"
            if name in ("Bending stress", "Shear strength", "Support bearing") and limit_value > 0:
                passed = value <= limit_value
                status, status_color = ("Pass", "#237b57") if passed else ("Fail", "#b94a45")
            elif name in ("Total-load deflection", "Live-load deflection"):
                passed = value <= limit_value
                status, status_color = ("Pass", "#237b57") if passed else ("Fail", "#b94a45")
            tk.Label(box, text=name, bg="#fbfcfc", fg="#354c58", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
            tk.Label(box, text=status, bg="#eef2f4", fg=status_color, font=("Segoe UI", 8, "bold"),
                     padx=6, pady=2).place(relx=1.0, x=-10, y=8, anchor="ne")
            tk.Label(box, text=f"{value:.3f} {unit}", bg="#fbfcfc", fg="#273f4a",
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10)
            detail_text = f"{detail}; limit {limit_value:.3f} {unit}" if limit_value > 0 else f"{detail}; enter a limit"
            tk.Label(box, text=detail_text, bg="#fbfcfc", fg="#7f8e96",
                     font=("Segoe UI", 8), wraplength=300).pack(anchor="w", padx=10, pady=(2, 8))


def main():
    app = BeamDesignerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
