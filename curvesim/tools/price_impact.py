"""Compute bounded changes in a plain pool's marginal price."""
from dataclasses import dataclass
from math import isfinite

from curvesim.pool.sim_interface import SimCurvePool


class PriceImpactNotBracketed(ValueError):
    """The caller's maximum input does not bracket the target price."""


class ModelEvaluationError(RuntimeError):
    """The upstream model could not evaluate a trial trade or price."""


@dataclass(frozen=True)
# Preserve both bracket endpoints and diagnostic fields in one immutable result.
class PriceImpactResult:  # pylint: disable=too-many-instance-attributes
    """A crossing bracket for upstream's floating-point marginal price.

    Amounts use SimCurvePool's normalized 18-decimal units, not necessarily
    the underlying ERC20's base units. The bracket is NOT a proof of the
    economically minimal raw amount, exact contract execution or output.
    """

    amount_in: int
    amount_out: int
    fee_amount: int
    initial_price: float
    target_price: float
    post_trade_price: float
    lower_amount_in: int
    lower_post_trade_price: float
    use_fee: bool
    evaluations: int


# Keep the endpoint prices/output/fees explicit while bisecting.
# pylint: disable-next=too-many-locals
def trade_size_for_price_impact(
    pool, coin_in, coin_out, impact, *, max_amount_in, use_fee=True
):
    """Find an input amount that lowers the directional marginal price.

    ``impact=0.01`` means ``target = initial_price * (1 - 0.01)``.
    Both prices quote coin_out per coin_in, using the SAME ``use_fee``.
    Trades always charge the pool's actual configured model fee; use_fee
    only controls the reported marginal-price convention.

    The supplied pool's current balances are used, with no rebalancing.
    Supported scope: the exact upstream SimCurvePool class, 2 or 3 coins,
    constant fee, positive balances and normalized rates. Metapools,
    crypto, dynamic fees and subclasses are explicitly unsupported.

    max_amount_in is a required positive integer in normalized units. No
    implicit reverse trade, cap extension or zero fallback is performed.
    A zero impact returns a zero trade; a positive target not bracketed by the cap
    raises PriceImpactNotBracketed. Invalid model evaluations raise
    ModelEvaluationError with their original cause.

    Integer bisection preserves a crossing in the FLOAT price returned by
    upstream. For positive impact the returned upper and lower amounts
    are adjacent integers, with p(lower) > target >= p(upper). This is a
    model diagnostic, NOT proof of a globally minimal economic raw amount:
    float plateaus, integer rounding and model-versus-contract differences
    remain. It assumes the constant-fee plain model's decreasing price
    path; it is not a general solver for arbitrary SimPool implementations.

    Every trial uses upstream's snapshot context, which restores balances
    and admin balances even when a trial raises. Do not concurrently mutate
    the same pool object while this synchronous calculation runs.
    """
    _validate_pool(pool)
    _validate_request(pool.n, coin_in, coin_out, impact, max_amount_in, use_fee)
    initial, _, _ = _evaluate(pool, coin_in, coin_out, 0, use_fee)
    evaluations = 1
    target = initial * (1 - impact)
    if impact == 0:
        return PriceImpactResult(
            0, 0, 0, initial, initial, initial, 0, initial, use_fee, evaluations
        )
    if not 0 < target < initial:
        raise ValueError(
            "The requested target is indistinguishable at upstream float precision"
        )

    low, high = 0, max_amount_in
    low_price = initial
    high_price, high_out, high_fee = _evaluate(pool, coin_in, coin_out, high, use_fee)
    evaluations += 1
    if high_price > target:
        raise PriceImpactNotBracketed(
            f"Target {target!r} not reached at max_amount_in={high}: price={high_price!r}"
        )
    while high - low > 1:
        mid = (low + high) // 2
        price, output, fee = _evaluate(pool, coin_in, coin_out, mid, use_fee)
        evaluations += 1
        if price <= target:
            high, high_price, high_out, high_fee = mid, price, output, fee
        else:
            low, low_price = mid, price
    return PriceImpactResult(
        high,
        high_out,
        high_fee,
        initial,
        target,
        high_price,
        low,
        low_price,
        use_fee,
        evaluations,
    )


def _validate_pool(pool):
    # Exact class identity excludes implementations with different price paths.
    if type(pool) is not SimCurvePool:  # pylint: disable=unidiomatic-typecheck
        raise TypeError("Only the exact plain SimCurvePool class is supported")
    if pool.n not in (2, 3) or pool.fee_mul is not None:
        raise ValueError("Only 2/3-coin plain pools with constant fees are supported")
    if not all(_is_int(value) for value in (pool.A, pool.fee, pool.admin_fee)):
        raise ValueError("Unsupported or invalid plain-pool parameters")
    if (
        pool.A <= 0
        or not 0 <= pool.fee < 10**10
        or not 0 <= pool.admin_fee <= 10**10
    ):
        raise ValueError("Unsupported or invalid plain-pool parameters")
    if len(pool.balances) != pool.n or any(
        not _is_int(b) or b <= 0 for b in pool.balances
    ):
        raise ValueError("Unsupported or invalid plain-pool parameters")
    if pool.rates != [10**18] * pool.n:
        raise ValueError("Unsupported or invalid plain-pool parameters")


def _is_int(value):
    # bool and arbitrary int subclasses are not valid normalized-amount inputs.
    return type(value) is int  # pylint: disable=unidiomatic-typecheck


def _validate_request(  # pylint: disable=too-many-arguments
    n_coins, coin_in, coin_out, impact, max_amount_in, use_fee
):
    if not isinstance(use_fee, bool):
        raise TypeError("use_fee must be a bool")
    if type(impact) not in (int, float):
        raise ValueError("impact must be a finite fraction in [0, 1)")
    if not 0 <= impact < 1:
        raise ValueError("impact must be a fraction in [0, 1), e.g. 0.01 for 1%")
    if not _is_int(max_amount_in) or not 0 < max_amount_in < 2**256:
        raise ValueError("max_amount_in must be a positive integer below 2**256")
    if any(not _is_int(i) or not 0 <= i < n_coins for i in (coin_in, coin_out)):
        raise ValueError("coin_in and coin_out must be valid integer indices")
    if coin_in == coin_out:
        raise ValueError("coin_in and coin_out must differ")


def _evaluate(pool, coin_in, coin_out, amount, use_fee):
    try:
        with pool.use_snapshot_context():
            output, fee = pool.trade(coin_in, coin_out, amount) if amount else (0, 0)
            price = pool.price(coin_in, coin_out, use_fee=use_fee)
            if not isfinite(price) or price <= 0:
                raise ValueError("Model returned a nonpositive/nonfinite price")
            return price, output, fee
    except Exception as exc:
        raise ModelEvaluationError(
            f"Upstream evaluation failed at input {amount}"
        ) from exc
