from __future__ import annotations

import math
from dataclasses import dataclass

from ..models import GestureTemplate, Point


RESAMPLE_COUNT = 64


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def path_length(points: list[Point]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(distance(a, b) for a, b in zip(points, points[1:]))


def resample(points: list[Point], count: int) -> list[Point]:
    if not points:
        return []
    if len(points) == 1:
        return points * count

    total = path_length(points)
    if total == 0:
        return [points[0]] * count

    interval = total / (count - 1)
    targets = [interval * index for index in range(count)]
    result: list[Point] = []
    traversed = 0.0
    target_index = 0

    for previous, current in zip(points, points[1:]):
        segment = distance(previous, current)
        if segment == 0:
            continue

        while target_index < len(targets) and traversed + segment >= targets[target_index]:
            local = (targets[target_index] - traversed) / segment
            result.append(
                (
                    previous[0] + local * (current[0] - previous[0]),
                    previous[1] + local * (current[1] - previous[1]),
                )
            )
            target_index += 1
        traversed += segment

    while len(result) < count:
        result.append(points[-1])
    return result


def smooth(points: list[Point], window: int = 2) -> list[Point]:
    if len(points) < 5:
        return list(points)

    result = [points[0]]
    for index in range(1, len(points) - 1):
        start = max(0, index - window)
        end = min(len(points), index + window + 1)
        chunk = points[start:end]
        result.append(
            (
                sum(x for x, _ in chunk) / len(chunk),
                sum(y for _, y in chunk) / len(chunk),
            )
        )
    result.append(points[-1])
    return result


def scale_to_unit(points: list[Point]) -> list[Point]:
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y
    scale = max(span_x, span_y, 1e-6)
    offset_x = (scale - span_x) / 2
    offset_y = (scale - span_y) / 2
    return [((x - min_x + offset_x) / scale, (y - min_y + offset_y) / scale) for x, y in points]


def translate_to_origin(points: list[Point]) -> list[Point]:
    center_x = sum(x for x, _ in points) / len(points)
    center_y = sum(y for _, y in points) / len(points)
    return [(x - center_x, y - center_y) for x, y in points]


def normalize(points: list[Point]) -> list[Point]:
    prepared = smooth(points)
    return translate_to_origin(scale_to_unit(resample(prepared, RESAMPLE_COUNT)))


def average_distance(points_a: list[Point], points_b: list[Point]) -> float:
    values = [distance(a, b) for a, b in zip(points_a, points_b)]
    return sum(values) / max(len(values), 1)


@dataclass
class GestureMatchResult:
    template: GestureTemplate | None
    confidence: float
    distance: float


class GestureMatcher:
    def match(self, candidate: list[Point], templates: list[GestureTemplate]) -> GestureMatchResult:
        if len(candidate) < 4 or not templates:
            return GestureMatchResult(template=None, confidence=0.0, distance=999.0)

        normalized = normalize(candidate)
        best_template: GestureTemplate | None = None
        best_distance = 999.0

        for template in templates:
            if not template.enabled or len(template.points) < 4:
                continue
            score = average_distance(normalized, normalize(template.points))
            if score < best_distance:
                best_distance = score
                best_template = template

        confidence = max(0.0, 1.0 - best_distance / 1.25)
        return GestureMatchResult(
            template=best_template,
            confidence=round(confidence, 4),
            distance=round(best_distance, 4),
        )
