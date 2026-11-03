from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import math

from app.core.clock import to_ist


def calculate_question_points(
    when_viewed: datetime,
    start_time: datetime,
    current_time: datetime,
    base_points: Decimal | float,
    end_time: datetime,
) -> Decimal:
    """
    Calculates dynamic question points based on sigmoid end-point floor and quadratic decay:

    1. X0 = Base Points
    2. T1 = (End_at - Start_at) in seconds (Total game time)
    3. T0 = (Is_viewed - Start_at) in seconds (Time at which question was first viewed)
    4. X1 = g(T0) -> Minimum/end points floor based on when the question was first opened:
           g(t) = ((0.50 * X0) / (1 + exp(-10 * ((t - T1/2) / T1)))) + (0.25 * X0)
    5. Quadratic decay from T0 to T1:
           a = (X0 - X1) / ((T1 - T0) ** 2)
           D(t) = a * ((t - T0) ** 2)
           f(t) = X0 - D(t)
    6. Xt = f(current_time - start_time)
    """
    X0 = float(base_points)
    if X0 <= 0:
        return Decimal("0.00")

    # Normalize all datetimes to IST for safe arithmetic
    start_dt = to_ist(start_time)
    end_dt = to_ist(end_time)
    viewed_dt = to_ist(when_viewed)
    curr_dt = to_ist(current_time)

    # Convert timestamps to elapsed seconds from game start
    T1 = (end_dt - start_dt).total_seconds()
    T0 = (viewed_dt - start_dt).total_seconds()
    t = (curr_dt - start_dt).total_seconds()

    # Guard: Invalid game duration or question viewed at/after game end
    if T1 <= 0 or T0 >= T1:
        return Decimal(str(base_points)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Guard: If solving before or at the moment it was viewed (no decay yet)
    if t <= T0:
        return Decimal(str(base_points)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 1. Calculate X1 (End points floor via sigmoid function_g)
    exponent = max(-50.0, min(50.0, -10.0 * ((T0 - (T1 / 2.0)) / T1)))
    denom = 1.0 + math.exp(exponent)
    X1 = ((0.50 * X0) / denom) + (0.25 * X0)

    # Guard: If solved at or after game end, return end point floor X1
    if t >= T1:
        return Decimal(str(round(X1, 2))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 2. Quadratic decay coefficient
    a = (X0 - X1) / ((T1 - T0) ** 2)
    D_t = a * ((t - T0) ** 2)

    # 3. Current points Xt
    Xt = X0 - D_t

    # Clamp between X1 (minimum) and X0 (maximum)
    Xt_clamped = max(X1, min(X0, Xt))

    return Decimal(str(round(Xt_clamped, 2))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_hint_value(point, multiplier):
    pass


def calculate_retry_value(point, multiplier):
    pass


def calculate_block_time(point, multiplier):
    pass


def calculate_unblock_cost(time, multiplier):
    pass
