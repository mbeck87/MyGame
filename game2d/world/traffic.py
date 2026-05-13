"""Ampelzeiten, Beschilderung und Kreuzungs-Vorfahrt."""
import math

from game2d.config import BLOCK
from game2d.state import current
from game2d.world.geometry import road_connections_at

LIGHT_RED = 2.1
LIGHT_RED_YELLOW = 0.55
LIGHT_GREEN = 5.2
LIGHT_YELLOW = 0.9

CONTROL_LIGHT = "light"
CONTROL_STOP = "stop"
CONTROL_PRIORITY = "priority"


def _is_controlled_intersection(ix, iy, state):
    has_north, has_south, has_west, has_east = road_connections_at(ix, iy, state)
    approaches = sum((has_north, has_south, has_west, has_east))
    return approaches >= 3 and (has_north or has_south) and (has_west or has_east)


def _priority_axis(ix, iy, connections):
    has_north, has_south, has_west, has_east = connections
    ns_through = has_north and has_south
    ew_through = has_west and has_east
    if ns_through and not ew_through:
        return "NS"
    if ew_through and not ns_through:
        return "EW"
    gx = int(round(ix / BLOCK))
    gy = int(round(iy / BLOCK))
    if gx % 3 == 0:
        return "NS"
    if gy % 3 == 0:
        return "EW"
    return "NS" if gx % 2 == 0 else "EW"


def build_traffic_controls(state):
    """Build deterministic traffic rules for each real intersection."""
    state.traffic_controls.clear()
    for ix in state.roads_v:
        for iy in state.roads_h:
            if not _is_controlled_intersection(ix, iy, state):
                continue
            gx = int(round(ix / BLOCK))
            gy = int(round(iy / BLOCK))
            connections = road_connections_at(ix, iy, state)
            four_way = all(connections)

            if four_way and (gx + gy) % 5 == 0:
                state.traffic_controls[(ix, iy)] = {"type": CONTROL_LIGHT, "priority_axis": None}
                continue

            state.traffic_controls[(ix, iy)] = {
                "type": CONTROL_PRIORITY,
                "priority_axis": _priority_axis(ix, iy, connections),
                "side_rule": CONTROL_STOP if (gx * 7 + gy * 3) % 6 == 0 else "yield",
            }


def traffic_control_at(ix, iy):
    return current().traffic_controls.get((ix, iy))


def car_axis(car):
    return "NS" if car.is_vertical() else "EW"


def traffic_light_state(ix, iy):
    s = current()
    cycle = (LIGHT_RED + LIGHT_RED_YELLOW + LIGHT_GREEN + LIGHT_YELLOW) * 2
    offset = ((ix // BLOCK + iy // BLOCK) % 2) * (cycle * 0.5)
    t = (s.traffic_time + offset) % cycle
    phase = t % (cycle * 0.5)
    active_axis = 'NS' if t < cycle * 0.5 else 'EW'
    if phase < LIGHT_RED:
        return active_axis, 'red'
    if phase < LIGHT_RED + LIGHT_RED_YELLOW:
        return active_axis, 'red_yellow'
    if phase < LIGHT_RED + LIGHT_RED_YELLOW + LIGHT_GREEN:
        return active_axis, 'green'
    return active_axis, 'yellow'


def traffic_light_allows(car):
    zone = car.upcoming_intersection(82)
    if not zone:
        return True
    ix, iy, rect = zone
    control = traffic_control_at(ix, iy)
    if control and control.get("type") != CONTROL_LIGHT:
        return True
    if rect.collidepoint(car.x, car.y):
        return True
    axis, phase = traffic_light_state(ix, iy)
    return phase in ('green', 'yellow') and ((axis == 'NS') == car.is_vertical())


def _same_intersection(zone, ix, iy):
    return zone and abs(zone[0] - ix) <= 6 and abs(zone[1] - iy) <= 6


def _approaching_priority_conflict(car, ix, iy, priority_axis):
    my_axis = car_axis(car)
    for other in current().cars:
        if other is car or other.dead or other.sunk or other.driver is None:
            continue
        other_axis = car_axis(other)
        other_zone = other.upcoming_intersection(145)
        if not other_zone:
            other_zone = other.upcoming_intersection(70)
        if not _same_intersection(other_zone, ix, iy):
            continue
        other_dist = math.hypot(other.x - ix, other.y - iy)
        other_in_box = other_zone[2].inflate(58, 58).colliderect(other.rect())
        if other_axis == priority_axis and (other_in_box or other_dist < 185):
            return True
        if other_axis != my_axis and other_dist < 70:
            return True
    return False


def traffic_rule_allows(car, dt):
    zone = car.upcoming_intersection(102)
    if not zone:
        car._traffic_rule_key = None
        car._traffic_stop_timer = 0.0
        return True
    ix, iy, rect = zone
    control = traffic_control_at(ix, iy)
    if not control:
        return True
    control_type = control.get("type")
    key = (ix, iy, control_type, car_axis(car))

    if rect.collidepoint(car.x, car.y):
        return True

    if control_type == CONTROL_LIGHT:
        return traffic_light_allows(car)

    if control_type == CONTROL_STOP:
        if car._traffic_rule_key != key:
            car._traffic_rule_key = key
            car._traffic_stop_timer = 0.65
        if abs(car.spd) > 12:
            return False
        car._traffic_stop_timer = max(0.0, car._traffic_stop_timer - dt)
        return car._traffic_stop_timer <= 0.0

    if control_type == CONTROL_PRIORITY:
        priority_axis = control.get("priority_axis")
        if car_axis(car) == priority_axis:
            return True
        if control.get("side_rule") == CONTROL_STOP:
            if car._traffic_rule_key != key:
                car._traffic_rule_key = key
                car._traffic_stop_timer = 0.65
            if abs(car.spd) > 12:
                return False
            car._traffic_stop_timer = max(0.0, car._traffic_stop_timer - dt)
            if car._traffic_stop_timer > 0.0:
                return False
        if _approaching_priority_conflict(car, ix, iy, priority_axis):
            car.yield_timer = max(car.yield_timer, 0.22)
            return False
        return True

    return True


def intersection_has_sign_control(ix, iy):
    control = traffic_control_at(ix, iy)
    return bool(control and control.get("type") in (CONTROL_STOP, CONTROL_PRIORITY))
