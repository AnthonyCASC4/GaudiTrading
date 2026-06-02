"""Retirement projection engine — shows how consistent investing transforms futures."""

from dataclasses import dataclass

# Social Security estimates (2024 averages)
SS_AVERAGE_MONTHLY = 1_907  # Average monthly SS benefit
SS_MAX_MONTHLY = 4_873      # Maximum monthly SS benefit at full retirement age
COMFORTABLE_RETIREMENT_MONTHLY = 5_000  # What most financial planners suggest as minimum


@dataclass
class YearSnapshot:
    year: int
    age: int
    total_contributed: float
    portfolio_value: float
    growth_earned: float  # total gains from market


@dataclass
class RetirementProjection:
    monthly_contribution: float
    annual_return: float
    years: int
    starting_age: int
    starting_balance: float
    snapshots: list[YearSnapshot]
    final_value: float
    total_contributed: float
    total_growth: float
    monthly_retirement_income: float  # 4% rule
    ss_monthly: float
    combined_monthly: float
    gap_without_investing: float  # monthly shortfall with SS alone


def project_retirement(
    monthly_contribution: float,
    annual_return: float = 0.10,
    years: int = 30,
    starting_age: int = 25,
    starting_balance: float = 0.0,
    inflation_rate: float = 0.03,
) -> RetirementProjection:
    """
    Calculate how consistent monthly investing grows over time.

    Uses real return (return - inflation) for honest projections.
    Applies the 4% rule for sustainable retirement withdrawals.
    """
    real_return = annual_return - inflation_rate
    monthly_rate = real_return / 12

    balance = starting_balance
    total_contributed = starting_balance
    snapshots = []

    for year in range(1, years + 1):
        for month in range(12):
            balance = balance * (1 + monthly_rate) + monthly_contribution
        total_contributed += monthly_contribution * 12
        growth = balance - total_contributed

        snapshots.append(YearSnapshot(
            year=year,
            age=starting_age + year,
            total_contributed=round(total_contributed, 2),
            portfolio_value=round(balance, 2),
            growth_earned=round(growth, 2),
        ))

    # 4% rule: withdraw 4% per year for sustainable retirement income
    annual_withdrawal = balance * 0.04
    monthly_income = annual_withdrawal / 12

    return RetirementProjection(
        monthly_contribution=monthly_contribution,
        annual_return=annual_return,
        years=years,
        starting_age=starting_age,
        starting_balance=starting_balance,
        snapshots=snapshots,
        final_value=round(balance, 2),
        total_contributed=round(total_contributed, 2),
        total_growth=round(balance - total_contributed, 2),
        monthly_retirement_income=round(monthly_income, 2),
        ss_monthly=SS_AVERAGE_MONTHLY,
        combined_monthly=round(monthly_income + SS_AVERAGE_MONTHLY, 2),
        gap_without_investing=round(COMFORTABLE_RETIREMENT_MONTHLY - SS_AVERAGE_MONTHLY, 2),
    )


def compare_scenarios(
    starting_age: int = 25,
    monthly_amounts: list[float] | None = None,
    years_list: list[int] | None = None,
    annual_return: float = 0.10,
) -> dict:
    """
    Compare multiple investment scenarios side by side.
    Shows the power of starting early and being consistent.
    """
    if monthly_amounts is None:
        monthly_amounts = [50, 100, 200, 300, 500]
    if years_list is None:
        years_list = [5, 10, 20, 30]

    results = {}
    for amount in monthly_amounts:
        results[amount] = {}
        for years in years_list:
            proj = project_retirement(
                monthly_contribution=amount,
                annual_return=annual_return,
                years=years,
                starting_age=starting_age,
            )
            results[amount][years] = {
                "final_value": proj.final_value,
                "total_contributed": proj.total_contributed,
                "total_growth": proj.total_growth,
                "monthly_retirement_income": proj.monthly_retirement_income,
                "retirement_age": starting_age + years,
            }

    return {
        "scenarios": results,
        "context": {
            "ss_average_monthly": SS_AVERAGE_MONTHLY,
            "ss_max_monthly": SS_MAX_MONTHLY,
            "comfortable_retirement_monthly": COMFORTABLE_RETIREMENT_MONTHLY,
            "gap_ss_only": COMFORTABLE_RETIREMENT_MONTHLY - SS_AVERAGE_MONTHLY,
            "note": "All values in today's dollars (adjusted for ~3% inflation). "
                    "Uses the 4% rule for sustainable retirement withdrawals.",
        },
    }


def savings_account_comparison(
    monthly_contribution: float,
    years: int,
    savings_rate: float = 0.045,  # typical high-yield savings
    market_return: float = 0.10,
) -> dict:
    """Show the difference between saving in a bank vs investing in VOO."""
    savings_balance = 0.0
    invest_balance = 0.0
    savings_monthly = savings_rate / 12
    invest_monthly = (market_return - 0.03) / 12  # real return

    for _ in range(years * 12):
        savings_balance = savings_balance * (1 + savings_monthly) + monthly_contribution
        invest_balance = invest_balance * (1 + invest_monthly) + monthly_contribution

    total_put_in = monthly_contribution * years * 12

    return {
        "monthly_contribution": monthly_contribution,
        "years": years,
        "total_contributed": round(total_put_in, 2),
        "savings_account": {
            "final_value": round(savings_balance, 2),
            "growth": round(savings_balance - total_put_in, 2),
            "rate": f"{savings_rate*100:.1f}%",
        },
        "invested_in_voo": {
            "final_value": round(invest_balance, 2),
            "growth": round(invest_balance - total_put_in, 2),
            "rate": f"{market_return*100:.1f}% (historical avg)",
        },
        "difference": round(invest_balance - savings_balance, 2),
        "note": "Investment values adjusted for inflation. Past performance doesn't guarantee future results, but history spans 90+ years.",
    }
