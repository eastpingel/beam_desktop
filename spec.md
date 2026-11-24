# Beam Designer

## Purpose

Show shear, moment, and deflection diagrams for a beam and provide preliminary strength and stiffness checks. This is a screening tool, not a substitute for a complete structural design or review.

## Application platform

- This project is a native desktop application written in Python.
- Use the standard-library Tkinter toolkit for the graphical user interface.
- Keep the engineering calculations and property data separate from the Tkinter presentation code so they can be tested without launching the GUI.
- Use only standard-library or explicitly approved third-party packages. Do not assume a web browser or web framework is required.
- Target Windows and conventional desktop Python installations. The application must start from a Python entry-point script.

## Interface structure

- Open with one main Tkinter window.
- Divide the window into input controls, a beam and loading drawing, shear/moment/deflection plots, and a results panel.
- Use labels and validation feedback to identify units and invalid or missing inputs.
- Keep the sample W12x26 beam and loading visible and usable as the initial example.
- Display selected member properties and calculation assumptions alongside the results.
- Provide a File menu with Save and Open commands.
- Save beam files in JSON format containing the support type, span, selected section and section properties, deflection limit, uniform loads, point loads, material/product, property source, and self-weight setting.
- Open restores the saved beam model and immediately reruns the analysis.

## First-version beam list

- **Steel:** a curated subset of rolled W-shapes. Proposed starter list: W8x10, W8x18, W10x12, W10x22, W12x14, W12x26, W14x22, W16x26, W18x35, and W21x44. Verify each designation against the selected AISC Shapes Database before use.
- **Solid-sawn lumber:** rectangular dimensional members with nominal sizes 2x4, 2x6, 2x8, 2x10, 2x12, 4x4, 4x6, 4x8, and 6x6. Proposed initial species/grade combinations: Douglas Fir-Larch No. 2, Southern Pine No. 2, Spruce-Pine-Fir No. 2, and Hem-Fir No. 2. Verify each combination and size against the selected design-value source.
- **Engineered lumber:** include both laminated veneer lumber (LVL) and glued-laminated timber (glulam). Exact manufacturers/products, grades, and sizes must be tied to the property source for each record.
- Other steel shapes and built-up/custom sections are out of scope for the first version.

## Inputs

- Support condition: simply supported or cantilever.
- Span, entered in feet.
- A selected beam from the proposed lists above.
- Full-span uniform loads and point loads at user-specified positions. Partial-span uniform loads are out of scope for the first version.
- Allow users to choose whether beam self-weight is added automatically from the property data or excluded.
- Use user-entered service loads; code-based load combinations are out of scope for the first version.
- Material properties associated with the selected beam. Do not assume one generic allowable stress for all steel or lumber members.

## Beam-property data

- Steel records should provide the shape designation, section dimensions, area, Ix, Sx, Zx, self-weight, and the material properties needed by the selected checks.
- Lumber records should provide nominal and actual dimensions, Ix, Sx, self-weight, species or product, grade, and the material properties needed by the selected checks.
- Start with a small manually curated prototype table. Record the source and edition/version for every property's value, and do not mix design provisions and design values from different editions.
- **Steel section geometry:** use the AISC Shapes Database v16.0 for W-shape dimensions and section properties. Steel grade properties must be associated with an explicitly identified grade; do not infer them from the shape designation.
- **Solid-sawn lumber and glulam design values:** use the American Wood Council (AWC) 2024 National Design Specification (NDS) and 2024 NDS Supplement, applying their published addenda and errata. The Supplement includes design values for sawn lumber and structural glued-laminated timber.
- **LVL design values:** use product-specific manufacturer technical data and a current code evaluation report where available. APA product certification/trademark documentation may be used to verify product qualification, but do not substitute generic LVL values for the selected product's published properties.
- Preserve the citation, edition/date, units, and product/grade identifier with each manually entered record.
- Display the selected beam and relevant properties so users can see what values the analysis uses.

## Calculations and checks

- Calculate support reactions and shear and moment along the beam using statics.
- Calculate elastic deflection for the modeled beam and loads.
- Calculate bending stress (`fb = M/S`) and compare it with an applicable allowable value for the selected material and method. The method and required material adjustments need to be specified before treating this as a design check.
- Compare both live-load and total-load deflection with an `L/360` limit.
- Include shear-strength and support/bearing checks. Define and show the applicable material properties, support assumptions, and capacity criteria used by these checks.
- Do not imply that passing the implemented checks establishes overall beam adequacy. Buckling and other unimplemented limit states are outside the check and must be identified as such in the results.

## Outputs

- A beam drawing with its supports and loads.
- Shear, moment, and deflection diagrams.
- Results for each implemented check, with pass/fail, calculated value, limit, and the assumptions/property values used.
- A clear notice that checks not implemented by the app are not evaluated.

## Look and feel

Clean and professional, with a fully specified example beam and loading shown when the app opens.

## Validation

- Initial baseline: 20 ft simply supported W12x26 with a 1 kip/ft uniform load across the full span. For the reference results, exclude self-weight. Expected reactions are 10 kip at each support, maximum shear magnitude is 10 kip, maximum moment is 50.0 kip-ft, and the current expected deflection is 0.609 in. Confirm the material modulus and section properties used so the deflection result is reproducible.
- The W12x26 baseline is the only initial validation case. Additional cases may be added later.
- Compare reactions and diagram extrema as well as deflections; document units and assumptions for the baseline.

## Out of scope

- Continuous beams and buckling checks.
- Any strength or serviceability limit state not explicitly listed under Calculations and checks.

## Decisions and remaining questions

The following first-version choices were confirmed:

- Use a curated subset of steel W-shapes, plus the listed solid-sawn lumber sizes and engineered lumber.
- Begin with a small manually curated property table, documenting sources and editions for values.
- Support full-span uniform loads and point loads at user-specified positions.
- Let users choose whether beam self-weight is included automatically.
- Check both live-load and total-load deflection against L/360.
- Include bending, deflection, shear-strength, and support/bearing checks, with explicit limitations.
- Use user-entered service loads, without code-based load combinations.
- Start validation with only the W12x26 baseline case.

The scope choices below have been confirmed. The starter member lists are proposed and must be checked against their property sources before they are used:

- Use the proposed curated W-shape list and verify the designations against AISC Shapes Database v16.0.
- Use the listed lumber sizes and proposed species/grade combinations, subject to verification against the AWC 2024 NDS Supplement.
- Include LVL and glulam, with properties tied to the selected product and source.
- Select authoritative source references and editions before entering property values.

Still to finalize: the exact steel grade, the LVL/glulam products and sizes, and the source-backed property records for all listed members.

## Property references

- [AISC Shapes Database v16.0](https://www.aisc.org/aisc/publications/steel-construction-manual/shapes-database-v160/) — steel W-shape dimensions and section properties.
- [AWC 2024 NDS](https://awc.org/publications/2024-nds/) and [2024 NDS Supplement](https://awc.org/publications/2024-nds-supplement/) — wood design provisions and design values. Use the same edition for provisions and values, including applicable published updates.
- [APA Glulam resources](https://www.apawood.org/engineered-wood-products/glulam/) — product identification and glulam design tables; use with the applicable NDS edition.
- [APA Structural Composite Lumber resources](https://www.apawood.org/engineered-wood-products/structural-composite-lumber-scl/) — LVL category and qualification context. Use product-specific technical data and applicable evaluation reports for LVL values.
