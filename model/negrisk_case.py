"""Research comparison, not a venue integration or price simulation.

Run: python3 -B -m model.negrisk_case

Compares backing for a numeric-observation portfolio under this ledger's
whole-account rule against the inspected Polymarket NegRiskAdapter operations.
All arithmetic is rational. No Solidity is executed and no deployed market is
measured; the adapter is reimplemented from source at the pinned commit.
"""
from fractions import Fraction as F
import json
from pathlib import Path

from .payoffs import Payoff

NEGRISK_COMMIT = "f78b35b0863b4308a431ca307d06f49b2ea65e78"
FEE_BIPS = 0  # md.feeBips(); zero isolates backing from fee policy.


# --------------------------------------------------------------------------
# Adapter model, transcribed from the inspected source.
#
#   splitPosition(conditionId, amount)   line 124: caller pays `amount`
#                                        collateral, receives amount YES + NO.
#   mergePositions(conditionId, amount)  line 158: the inverse.
#   convertPositions(marketId, indexSet, amount)  line 244:
#       - reverts unless questionCount > 1
#       - indexSet is a bitmask bounded by that market's questionCount
#       - burns the caller's NO tokens named by indexSet
#       - returns amountOut YES for every complement question
#       - releases (popcount(indexSet) - 1) * amountOut collateral
# Every operation takes a single marketId or conditionId.
# --------------------------------------------------------------------------


def numeric_zero(profile) -> bool:
    """True when the profile pays zero at every numeric result.

    VOID is excluded deliberately. The CTF has no VOID analogue in this model,
    so exceptional-resolution semantics are not compared; only numeric terminal
    payoffs are matched.
    """
    return profile.base == 0 and not profile.knots


def asce_backing(profile):
    """Whole-account rule: fund the infimum of the combined profile."""
    return max(F(0), -profile.minimum)


class NegRiskMarket:
    """One neg-risk market: an ordered, exhaustive, mutually exclusive partition."""

    def __init__(self, name, boundaries):
        self.name = name
        self.boundaries = list(boundaries)
        self.questions = []
        lo = None
        for hi in self.boundaries + [None]:
            self.questions.append((lo, hi))
            lo = hi

    @property
    def count(self):
        return len(self.questions)

    def indicator(self, index):
        lo, hi = self.questions[index]
        if lo is None and hi is None:
            return Payoff.constant(1)
        if lo is None:
            return Payoff.below(hi, 1, void=0)
        if hi is None:
            return Payoff.step(lo, 1, void=0)
        return Payoff.interval(lo, hi, 1, void=0)

    def partitions_the_line(self):
        """Exactly one question pays at every numeric result."""
        total = Payoff.constant(0)
        for i in range(self.count):
            total = total + self.indicator(i)
        return numeric_zero(total - Payoff.constant(1))


class AdapterAccount:
    """Tracks collateral paid in and token holdings under the adapter's rules."""

    def __init__(self):
        self.collateral_in = F(0)
        self.tokens = {}

    def _move(self, key, amount):
        self.tokens[key] = self.tokens.get(key, F(0)) + amount
        if self.tokens[key] == 0:
            del self.tokens[key]

    def split(self, market, index, amount):
        self.collateral_in += amount
        self._move((market.name, index, True), amount)
        self._move((market.name, index, False), amount)

    def merge(self, market, index, amount):
        for is_yes in (True, False):
            if self.tokens.get((market.name, index, is_yes), F(0)) < amount:
                raise ValueError("merge requires both sides of one condition")
        self.collateral_in -= amount
        self._move((market.name, index, True), -amount)
        self._move((market.name, index, False), -amount)

    def sell_yes(self, market, index, amount, premium=F(0)):
        if self.tokens.get((market.name, index, True), F(0)) < amount:
            raise ValueError("cannot sell YES not held")
        self._move((market.name, index, True), -amount)
        self.collateral_in -= premium

    def convert(self, market, index_set, amount):
        if market.count <= 1:
            raise ValueError("NoConvertiblePositions")
        if not index_set:
            raise ValueError("InvalidIndexSet")
        if max(index_set) >= market.count:
            raise ValueError("InvalidIndexSet")
        for i in index_set:
            if self.tokens.get((market.name, i, False), F(0)) < amount:
                raise ValueError("insufficient NO balance")
        out = amount - amount * F(FEE_BIPS, 10_000)
        for i in index_set:
            self._move((market.name, i, False), -amount)
        for i in range(market.count):
            if i not in index_set:
                self._move((market.name, i, True), out)
        if len(index_set) > 1:
            self.collateral_in -= (len(index_set) - 1) * out

    def profile(self, markets):
        """Terminal numeric payoff of everything held."""
        total = Payoff.constant(0)
        for (mname, index, is_yes), amount in self.tokens.items():
            claim = markets[mname].indicator(index)
            if not is_yes:
                claim = Payoff.constant(1) - claim
            total = total + claim * amount
        return total


def best_convert_release(account, market, amount):
    """Give the adapter its best move: search every legal index set in one market."""
    best, best_set = F(0), None
    for mask in range(1, 1 << market.count):
        index_set = {i for i in range(market.count) if mask & (1 << i)}
        if any(account.tokens.get((market.name, i, False), F(0)) < amount
               for i in index_set):
            continue
        release = (len(index_set) - 1) * amount * (1 - F(FEE_BIPS, 10_000))
        if release > best:
            best, best_set = release, sorted(index_set)
    return best, best_set


def lifecycle():
    """Two steps: an aligned package, then a boundary the partition cannot express."""
    M = NegRiskMarket("M", [3000, 3200])
    N = NegRiskMarket("N", [3000, 3100])
    markets = {"M": M, "N": N}
    assert M.partitions_the_line() and N.partitions_the_line()

    steps = []

    # Step 1: sell the two outer claims of M. They are mutually exclusive and
    # both are declared questions of the same market, so convert applies.
    sold = M.indicator(0) + M.indicator(2)
    asce_step1 = asce_backing(Payoff.constant(0) - sold)
    asce = Payoff.constant(1) - sold

    acct = AdapterAccount()
    acct.split(M, 0, F(1))
    acct.split(M, 2, F(1))
    acct.sell_yes(M, 0, F(1))
    acct.sell_yes(M, 2, F(1))
    release, index_set = best_convert_release(acct, M, F(1))
    acct.convert(M, {0, 2}, F(1))
    steps.append({
        "step": "sell both outer claims of one declared partition",
        "asce_backing": str(asce_step1),
        "adapter_backing": str(acct.collateral_in),
        "adapter_best_convert_release": str(release),
        "adapter_convert_index_set": index_set,
        "profiles_match": numeric_zero(acct.profile(markets) - asce),
    })

    # Step 2: sell a claim whose boundary falls inside an existing question.
    new_claim = N.indicator(1)                       # pays on [3000, 3100)
    asce_after = asce - new_claim
    asce_extra = max(F(0), -asce_after.minimum)

    before = acct.collateral_in
    acct.split(N, 1, F(1))
    acct.sell_yes(N, 1, F(1))
    release_n, index_set_n = best_convert_release(acct, N, F(1))
    adapter_extra = acct.collateral_in - before - release_n

    residual = acct.profile(markets) - asce_after
    steps.append({
        "step": "sell a claim with a boundary the partition cannot express",
        "asce_additional_backing": str(asce_extra),
        "adapter_additional_backing": str(adapter_extra),
        "adapter_best_convert_release_in_new_market": str(release_n),
        "adapter_convert_index_set": index_set_n,
        "residual_is_constant": not residual.knots,
        "trapped_constant": str(residual.base),
        "trapped_equals_gap": residual.base == adapter_extra - asce_extra,
    })

    asce_total = asce_step1 + asce_extra
    return {
        "asce_total_backing": str(asce_total),
        "adapter_total_backing": str(acct.collateral_in),
        "gap": str(acct.collateral_in - asce_total),
        "steps": steps,
    }


def scaling(refinements=4):
    """Each further refinement needs a new marketId and earns no conversion relief."""
    M = NegRiskMarket("M", [3000, 3200])
    markets = {"M": M}
    held = M.indicator(1)                            # [3000, 3200) after step 1
    acct = AdapterAccount()
    acct.collateral_in = F(1)                        # backing carried from step 1
    asce_total = F(1)
    rows = []
    lower, upper = 3000, 3200
    for j in range(refinements):
        cut = lower + (upper - lower) // 2
        market = NegRiskMarket(f"R{j}", [lower, cut])
        markets[market.name] = market
        assert market.partitions_the_line()

        held = held - Payoff.interval(lower, cut, 1, void=0)
        asce_total += max(F(0), -held.minimum)

        acct.split(market, 1, F(1))
        acct.sell_yes(market, 1, F(1))
        release, _ = best_convert_release(acct, market, F(1))
        assert release == 0, "a lone NO position releases nothing"

        rows.append({
            "refinement": j + 1,
            "boundary_added": cut,
            "asce_total_backing": str(asce_total),
            "adapter_total_backing": str(acct.collateral_in),
            "convert_release_available": str(release),
        })
        lower = cut
    return rows


def separability_certificate():
    """Why no rearrangement helps: every adapter operation is single-market."""
    return {
        "split_scope": "one conditionId",
        "merge_scope": "one conditionId, requires both YES and NO of that condition",
        "convert_scope": "one marketId, indexSet bounded by questionCount",
        "question_membership": "only the market oracle may add a question (OnlyOracle)",
        "cross_market_operation_exists": False,
        "consequence": "adapter backing is additively separable across marketIds",
        "asce_rule": "single infimum over the combined account profile",
    }


def run():
    results = {
        "status": "exact rational arithmetic; adapter reimplemented from source",
        "source_repo": "Polymarket/neg-risk-ctf-adapter",
        "source_commit": NEGRISK_COMMIT,
        "fee_bips": FEE_BIPS,
        "observation": "one numeric terminal observation, one settlement asset",
        "lifecycle": lifecycle(),
        "scaling": scaling(),
        "certificate": separability_certificate(),
        "not_established": [
            "no Solidity executed and no deployed Polymarket market measured",
            "no claim about prices, liquidity, spreads or fees on either venue",
            "zero premiums assumed on both sides to isolate backing",
            "assumes an oracle would list the refined market at all",
            "token precision and Solidity rounding not modelled",
            "VOID and invalid-resolution semantics excluded from the comparison",
        ],
    }
    path = Path(__file__).resolve().parent.parent / "research" / "negrisk-case-results.json"
    path.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run()
