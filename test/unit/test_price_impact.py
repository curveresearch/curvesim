"""Tests for the bounded plain-pool marginal price impact helper."""
import copy
import math
import unittest
from unittest.mock import patch

from curvesim.pipelines.common import get_arb_trades
from curvesim.pool import CurvePool
from curvesim.pool.sim_interface import SimCurvePool
from curvesim.tools.price_impact import (
    ModelEvaluationError,
    PriceImpactNotBracketed,
    trade_size_for_price_impact,
)

UNIT = 10**18


def make_pool(
    balances=(1_000_000, 1_000_000), A=100, fee=4_000_000, admin_fee=5_000_000_000
):
    return SimCurvePool(
        A=A,
        D=[b * UNIT for b in balances],
        n=len(balances),
        fee=fee,
        admin_fee=admin_fee,
    )


def state(pool):
    return {name: copy.deepcopy(getattr(pool, name)) for name in CurvePool.__slots__}


class PriceImpactTests(unittest.TestCase):
    def solve(self, pool, i=0, j=1, impact=0.01, **kwargs):
        before = state(pool)
        answer = trade_size_for_price_impact(
            pool, i, j, impact, max_amount_in=2_000_000 * UNIT, **kwargs
        )
        self.assertEqual(state(pool), before)
        if impact:
            self.assertEqual(answer.amount_in - answer.lower_amount_in, 1)
            self.assertGreater(answer.lower_post_trade_price, answer.target_price)
            self.assertLessEqual(answer.post_trade_price, answer.target_price)
            with pool.use_snapshot_context():
                output, fee = pool.trade(i, j, answer.amount_in)
                self.assertEqual(output, answer.amount_out)
                self.assertEqual(fee, answer.fee_amount)
                self.assertEqual(
                    pool.price(i, j, use_fee=answer.use_fee), answer.post_trade_price
                )
            self.assertEqual(state(pool), before)
        return answer

    def test_balanced_one_percent_and_admin_state_restored(self):
        pool = make_pool()
        pool.admin_balances = [1357, 2468]
        answer = self.solve(pool)
        self.assertEqual(answer.initial_price, 0.9996)
        self.assertEqual(answer.target_price, 0.9996 * 0.99)
        self.assertGreater(answer.amount_out, 0)
        self.assertGreater(answer.fee_amount, 0)

    def test_unbalanced_direction_is_explicit_and_target_is_relative(self):
        pool = make_pool((1_600_000, 400_000), A=30)
        forward = self.solve(pool, 0, 1)
        reverse = self.solve(pool, 1, 0)
        self.assertNotEqual(forward.amount_in, reverse.amount_in)
        self.assertLess(forward.initial_price, 1)
        self.assertGreater(reverse.initial_price, 1)
        self.assertEqual(forward.target_price, forward.initial_price * 0.99)
        self.assertEqual(reverse.target_price, reverse.initial_price * 0.99)

    def test_three_coin_unbalanced_model(self):
        self.solve(make_pool((1_200_000, 650_000, 2_000_000), A=250), 2, 1, 0.05)

    def test_fee_excluded_price_still_charges_actual_trade_fee(self):
        pool = make_pool()
        included = self.solve(pool, use_fee=True)
        excluded = self.solve(pool, use_fee=False)
        self.assertEqual(excluded.initial_price, 1.0)
        self.assertEqual(excluded.target_price, 0.99)
        self.assertGreater(excluded.fee_amount, 0)
        # Constant marginal fee factor cancels from the relative target.
        self.assertLess(abs(included.amount_in / excluded.amount_in - 1), 1e-10)

    def test_zero_fee_model(self):
        answer = self.solve(make_pool(fee=0))
        self.assertEqual(answer.fee_amount, 0)
        self.assertEqual(answer.initial_price, 1.0)

    def test_admin_fee_changes_post_trade_inventory_and_size(self):
        retained = self.solve(make_pool(admin_fee=0))
        removed = self.solve(make_pool(admin_fee=10**10))
        self.assertNotEqual(retained.amount_in, removed.amount_in)

    def test_marginal_after_price_is_not_average_execution_price(self):
        answer = self.solve(make_pool())
        average = answer.amount_out / answer.amount_in
        self.assertGreater(average, answer.post_trade_price)
        self.assertGreater(abs(average - answer.post_trade_price), 0.001)

    def test_zero_impact_is_the_only_zero_trade_result(self):
        pool = make_pool()
        with patch.object(
            SimCurvePool, "trade", side_effect=AssertionError("zero should not trade")
        ):
            answer = self.solve(pool, impact=0)
        self.assertEqual(
            (answer.amount_in, answer.amount_out, answer.fee_amount), (0, 0, 0)
        )
        self.assertEqual(answer.evaluations, 1)

    def test_target_not_bracketed_raises_and_restores(self):
        pool = make_pool()
        before = state(pool)
        with self.assertRaises(PriceImpactNotBracketed):
            trade_size_for_price_impact(pool, 0, 1, 0.2, max_amount_in=100 * UNIT)
        self.assertEqual(state(pool), before)

    def test_exception_after_trade_restores_both_balance_arrays(self):
        pool = make_pool()
        pool.admin_balances = [123, 456]
        before = state(pool)
        original_price = SimCurvePool.price

        def failing_price(obj, *args, **kwargs):
            if obj.balances != before["balances"]:
                raise ArithmeticError("prepared failure after real trade")
            return original_price(obj, *args, **kwargs)

        with patch.object(SimCurvePool, "price", failing_price):
            with self.assertRaises(ModelEvaluationError) as caught:
                trade_size_for_price_impact(
                    pool, 0, 1, 0.01, max_amount_in=2_000_000 * UNIT
                )
        self.assertIsInstance(caught.exception.__cause__, ArithmeticError)
        self.assertEqual(state(pool), before)

    def test_trade_exception_after_real_mutation_restores(self):
        pool = make_pool()
        before = state(pool)
        original_trade = SimCurvePool.trade

        def failing_trade(obj, *args):
            original_trade(obj, *args)
            raise ArithmeticError("prepared trade exception")

        with patch.object(SimCurvePool, "trade", failing_trade):
            with self.assertRaises(ModelEvaluationError):
                trade_size_for_price_impact(
                    pool, 0, 1, 0.01, max_amount_in=2_000_000 * UNIT
                )
        self.assertEqual(state(pool), before)

    def test_matches_existing_arbitrage_recipe_with_same_relative_target(self):
        pool = make_pool()
        answer = self.solve(pool)
        before = state(pool)
        trade = get_arb_trades(pool, {(0, 1): answer.target_price})[0]
        self.assertEqual((trade.coin_in, trade.coin_out), (0, 1))
        self.assertLess(abs(trade.amount_in / answer.amount_in - 1), 1e-10)
        self.assertEqual(state(pool), before)

    def test_issue_absolute_099_is_not_one_percent_from_fee_inclusive_initial(self):
        pool = make_pool()
        relative_impact_for_absolute_099 = 1 - 0.99 / pool.price(0, 1)
        self.assertAlmostEqual(relative_impact_for_absolute_099, 0.0096038415366146)
        self.assertNotEqual(relative_impact_for_absolute_099, 0.01)

    def test_small_positive_impact_lost_in_float_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "indistinguishable"):
            self.solve(make_pool(), impact=1e-30)

    def test_nonfinite_or_out_of_range_impact_rejected(self):
        for impact in (math.nan, math.inf, -0.01, 1, 10**1000, True, ".01"):
            with self.subTest(impact=impact), self.assertRaises(ValueError):
                self.solve(make_pool(), impact=impact)

    def test_invalid_direction_or_amount_units_rejected(self):
        pool = make_pool()
        for i, j in ((0, 0), (-1, 1), (0, 2), (True, 1), ("0", 1)):
            with self.subTest(pair=(i, j)), self.assertRaises(ValueError):
                self.solve(pool, i, j)
        for cap in (0, -1, 1.5, True, "1000", 2**256):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                trade_size_for_price_impact(pool, 0, 1, 0.01, max_amount_in=cap)

    def test_dynamic_fee_and_inherited_families_rejected(self):
        pool = make_pool()
        pool.fee_mul = 2 * 10**10
        with self.assertRaisesRegex(ValueError, "constant"):
            self.solve(pool)

        class DifferentPool(SimCurvePool):
            pass

        other = DifferentPool(A=100, D=[10**24, 10**24], n=2)
        with self.assertRaisesRegex(TypeError, "exact plain"):
            self.solve(other)
        with self.assertRaises(TypeError):
            trade_size_for_price_impact(
                CurvePool(A=100, D=2 * 10**24, n=2),
                0,
                1,
                0.01,
                max_amount_in=10**24,
            )

    def test_mutated_rates_or_pool_parameters_rejected(self):
        for key, value in (
            ("rates", [10**30, 10**18]),
            ("A", 0),
            ("fee", 10**10),
            ("admin_fee", -1),
        ):
            pool = make_pool()
            setattr(pool, key, value)
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.solve(pool)

    def test_amplification_sweep_on_real_upstream_instances(self):
        amounts = []
        for amplification in range(3, 41):
            answer = self.solve(make_pool(A=amplification))
            amounts.append(answer.amount_in)
        self.assertTrue(all(left < right for left, right in zip(amounts, amounts[1:])))
