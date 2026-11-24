"""Engineering calculations for the Beam Designer application."""

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class PointLoad:
    magnitude: float
    position: float
    kind: str = "live"


@dataclass(frozen=True)
class LoadCase:
    uniform: float
    points: tuple[PointLoad, ...]


@dataclass(frozen=True)
class Properties:
    elastic_modulus: float
    inertia: float
    section_modulus: float
    weight: float = 0.0


@dataclass(frozen=True)
class Statics:
    left_reaction: float
    right_reaction: float
    support_moment: float
    total: float


def make_load_case(
    live_uniform: float,
    other_uniform: float,
    points: Iterable[PointLoad],
    kind: str,
    include_self_weight: bool = False,
    self_weight_lb_ft: float = 0.0,
) -> LoadCase:
    point_tuple = tuple(points)
    if kind == "live":
        uniform = live_uniform
        selected_points = tuple(point for point in point_tuple if point.kind == "live")
    else:
        uniform = live_uniform + other_uniform
        selected_points = point_tuple
        if include_self_weight:
            uniform += self_weight_lb_ft / 1000.0
    return LoadCase(uniform=uniform, points=selected_points)


def solve_statics(span_ft: float, load_case: LoadCase, support: str) -> Statics:
    point_total = sum(point.magnitude for point in load_case.points)
    uniform_total = load_case.uniform * span_ft
    total = point_total + uniform_total
    moment_about_left = (
        load_case.uniform * span_ft * span_ft / 2.0
        + sum(point.magnitude * point.position for point in load_case.points)
    )

    if support == "cantilever":
        return Statics(total, 0.0, moment_about_left, total)

    left_reaction = moment_about_left / span_ft
    return Statics(left_reaction, total - left_reaction, 0.0, total)


def shear_at(span_ft: float, load_case: LoadCase, support: str, x_ft: float, statics: Statics) -> float:
    if support == "cantilever":
        return -(
            load_case.uniform * (span_ft - x_ft)
            + sum(point.magnitude for point in load_case.points if point.position > x_ft)
        )
    return (
        statics.left_reaction
        - load_case.uniform * x_ft
        - sum(point.magnitude for point in load_case.points if point.position <= x_ft)
    )


def moment_at(span_ft: float, load_case: LoadCase, support: str, x_ft: float, statics: Statics) -> float:
    if support == "cantilever":
        return -(
            load_case.uniform * (span_ft - x_ft) ** 2 / 2.0
            + sum(
                point.magnitude * (point.position - x_ft)
                for point in load_case.points
                if point.position > x_ft
            )
        )
    return (
        statics.left_reaction * x_ft
        - load_case.uniform * x_ft * x_ft / 2.0
        - sum(
            point.magnitude * (x_ft - point.position)
            for point in load_case.points
            if point.position <= x_ft
        )
    )


def get_coordinates(span_ft: float, points: Iterable[PointLoad], count: int = 500) -> list[float]:
    coordinates = [span_ft * index / count for index in range(count + 1)]
    epsilon = max(span_ft * 1e-7, 1e-8)
    for point in points:
        if point.position > 0:
            coordinates.append(max(0.0, point.position - epsilon))
        coordinates.append(point.position)
        if point.position < span_ft:
            coordinates.append(min(span_ft, point.position + epsilon))
    return sorted(set(coordinates))


def integrate_deflection(
    span_ft: float,
    load_case: LoadCase,
    properties: Properties,
    support: str,
    coordinates: Optional[list[float]] = None,
) -> list[tuple[float, float]]:
    if properties.elastic_modulus <= 0 or properties.inertia <= 0:
        return []

    span_in = span_ft * 12.0
    statics = solve_statics(span_ft, load_case, support)
    xs = coordinates if coordinates is not None else get_coordinates(span_ft, load_case.points)
    data: list[dict[str, float]] = []
    for x_ft in xs:
        moment = moment_at(span_ft, load_case, support, x_ft, statics) * 12.0
        data.append({
            "x": x_ft * 12.0,
            "curvature": -moment / (properties.elastic_modulus * properties.inertia),
        })

    slope = 0.0
    displacement = 0.0
    data[0]["raw_slope"] = 0.0
    data[0]["raw_displacement"] = 0.0
    for index in range(1, len(data)):
        dx = data[index]["x"] - data[index - 1]["x"]
        slope += (data[index - 1]["curvature"] + data[index]["curvature"]) * dx / 2.0
        displacement += (data[index - 1]["raw_slope"] + slope) * dx / 2.0
        data[index]["raw_slope"] = slope
        data[index]["raw_displacement"] = displacement

    initial_slope = -data[-1]["raw_displacement"] / span_in if support == "simple" else 0.0
    return [
        (point["x"] / 12.0, point["raw_displacement"] + initial_slope * point["x"])
        for point in data
    ]


def max_abs(values: Iterable[float]) -> tuple[int, float]:
    items = list(values)
    if not items:
        return 0, 0.0
    index = max(range(len(items)), key=lambda i: abs(items[i]))
    return index, items[index]
