"""Ampelzeiten und -logik."""
from game2d.config import BLOCK
from game2d.state import current

LIGHT_RED = 2.1
LIGHT_RED_YELLOW = 0.55
LIGHT_GREEN = 5.2
LIGHT_YELLOW = 0.9


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
    if rect.collidepoint(car.x, car.y):
        return True
    axis, phase = traffic_light_state(ix, iy)
    return phase in ('green', 'yellow') and ((axis == 'NS') == car.is_vertical())
