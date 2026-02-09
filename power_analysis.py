"""
Power Analysis for SWE-Sabotage Experimental Design
====================================================
Reproduces and validates all power calculations referenced in Section 5.3.

Dependencies: numpy, scipy (both in standard scientific Python installations).
No statsmodels required — all calculations from first principles.

Usage:
    python power_analysis.py

Author: Mat Gregory
Date: February 2026
"""

import numpy as np
from scipy import stats


def h1a_power(n_tasks: int = 50, true_rate: float = 0.20, alpha: float = 0.05):
    """
    H1a: Sabotage success rate > 0 (one-sided exact binomial test).

    H0: p = 0
    H1: p > 0

    Under H0 (p=0), P(k >= 1) = 0, so any k >= 1 rejects trivially.
    Power = P(k >= 1 | p = true_rate) = 1 - (1 - true_rate)^n.

    We also show a more conservative test against a small non-zero null
    (H0: p <= 0.01) to demonstrate p-values at various k.
    """
    print("=" * 70)
    print("H1a: Sabotage success rate > 0 (exact binomial test)")
    print("=" * 70)

    power = 1 - (1 - true_rate) ** n_tasks

    print(f"\n  Parameters: n={n_tasks}, assumed true rate={true_rate:.0%}, alpha={alpha}")
    print(f"  Power = 1 - (1-{true_rate})^{n_tasks} = {power:.6f}")
    print(f"\n  Under H0 (p=0), any k>=1 rejects. So power = P(k>=1 | p={true_rate}).")

    print(f"\n  Power across assumed true rates (n={n_tasks}):")
    print(f"  {'True rate':>10}  {'Power':>10}")
    for rate in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
        pwr = 1 - (1 - rate) ** n_tasks
        print(f"  {rate:>10.0%}  {pwr:>10.6f}")

    # More informative: p-values under a conservative null (p = 0.01)
    print(f"\n  p-values under conservative null H0: p <= 0.01 (one-sided):")
    print(f"  {'k successes':>12}  {'p-value':>10}")
    null_rate = 0.01
    for k in [1, 2, 3, 5, 10]:
        p_val = 1 - stats.binom.cdf(k - 1, n_tasks, null_rate)
        print(f"  {k:>12}  {p_val:>10.6f}")

    return power


def h1b_power(n_tasks: int = 50, sabotage_rate: float = 0.20,
              baseline_rate: float = 0.05, alpha: float = 0.05,
              n_sims: int = 10_000):
    """
    H1b: Sabotage rate > baseline (honest) rate.
    McNemar's exact test on paired binary outcomes.

    For each task, we observe (sabotage outcome, baseline outcome).
    The discordant pairs are:
        b = sabotage succeeds AND baseline fails
        c = sabotage fails AND baseline succeeds
    Under H0: P(b) = P(c), i.e. the instruction has no effect.
    One-sided test: is b significantly > c?

    Power estimated via simulation.
    """
    print("\n" + "=" * 70)
    print("H1b: Sabotage rate > baseline rate (McNemar's exact test)")
    print("=" * 70)
    print(f"\n  Parameters: n={n_tasks}, sabotage rate={sabotage_rate:.0%}, "
          f"baseline rate={baseline_rate:.0%}, alpha={alpha}")

    np.random.seed(42)
    rejections = 0

    for _ in range(n_sims):
        sab = np.random.binomial(1, sabotage_rate, n_tasks)
        bas = np.random.binomial(1, baseline_rate, n_tasks)

        b = np.sum((sab == 1) & (bas == 0))  # sabotage wins
        c = np.sum((sab == 0) & (bas == 1))  # baseline wins
        n_disc = b + c

        if n_disc == 0:
            continue

        # One-sided exact McNemar: P(B >= b | B ~ Binom(n_disc, 0.5))
        p_val = 1 - stats.binom.cdf(b - 1, n_disc, 0.5)

        if p_val < alpha:
            rejections += 1

    power = rejections / n_sims

    exp_b = n_tasks * sabotage_rate * (1 - baseline_rate)
    exp_c = n_tasks * (1 - sabotage_rate) * baseline_rate

    print(f"  Simulated power ({n_sims:,} simulations): {power:.4f}")
    print(f"\n  Expected discordant pairs per experiment:")
    print(f"    b (sabotage succeeds, baseline fails): {exp_b:.1f}")
    print(f"    c (sabotage fails, baseline succeeds):  {exp_c:.1f}")

    # Power across different baseline rates
    print(f"\n  Power across baseline rates "
          f"(n={n_tasks}, sabotage rate={sabotage_rate:.0%}):")
    print(f"  {'Baseline rate':>14}  {'Difference':>11}  {'Power':>8}")
    for br in [0.00, 0.02, 0.05, 0.10, 0.15]:
        rejs = 0
        for _ in range(n_sims):
            s = np.random.binomial(1, sabotage_rate, n_tasks)
            b_out = np.random.binomial(1, br, n_tasks)
            b_disc = np.sum((s == 1) & (b_out == 0))
            c_disc = np.sum((s == 0) & (b_out == 1))
            nd = b_disc + c_disc
            if nd == 0:
                continue
            pv = 1 - stats.binom.cdf(b_disc - 1, nd, 0.5)
            if pv < alpha:
                rejs += 1
        print(f"  {br:>14.0%}  {sabotage_rate - br:>11.0%}  {rejs / n_sims:>8.4f}")

    return power


def h2_power(n_tasks: int = 50, n_classes: int = 6, alpha: float = 0.05,
             n_sims: int = 10_000):
    """
    H2: Vulnerability class variation (chi-squared test of independence).

    Analytical power via the non-central chi-squared distribution,
    plus simulation with concrete per-class rates.
    """
    print("\n" + "=" * 70)
    print("H2: Vulnerability class variation (chi-squared test)")
    print("=" * 70)

    df = n_classes - 1
    tasks_per_class = n_tasks // n_classes

    print(f"\n  Parameters: {n_tasks} tasks across {n_classes} classes "
          f"(~{tasks_per_class} per class)")
    print(f"  df = {df}, alpha = {alpha}")

    # Analytical power using non-central chi-squared
    # Non-centrality parameter lambda = n * w^2
    chi2_crit = stats.chi2.ppf(1 - alpha, df)
    print(f"\n  Analytical power across effect sizes (Cohen's w):")
    print(f"  {'Effect size (w)':>16}  {'Interpretation':>16}  {'Power':>8}")
    for w, label in [(0.1, "small"), (0.2, "small-medium"),
                     (0.3, "medium"), (0.5, "large")]:
        ncp = n_tasks * w ** 2
        pwr = 1 - stats.ncx2.cdf(chi2_crit, df, ncp)
        print(f"  {w:>16.1f}  {label:>16}  {pwr:>8.4f}")

    # Sample size needed for 80% power at w = 0.3
    for n_test in range(10, 500):
        ncp = n_test * 0.3 ** 2
        pwr = 1 - stats.ncx2.cdf(chi2_crit, df, ncp)
        if pwr >= 0.80:
            print(f"\n  Sample size needed for 80% power at w=0.3: {n_test} tasks")
            break

    # Simulation with concrete rates
    true_rates = np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.35])
    print(f"\n  Simulation with concrete rates per class:")
    print(f"  True rates: {[f'{r:.0%}' for r in true_rates]}")
    print(f"  Tasks per class: {tasks_per_class}")

    np.random.seed(42)
    rejections = 0
    valid_sims = 0

    for _ in range(n_sims):
        successes = np.array([np.random.binomial(tasks_per_class, r)
                              for r in true_rates])
        failures = tasks_per_class - successes
        table = np.array([successes, failures])

        if np.any(table.sum(axis=0) == 0) or np.any(table.sum(axis=1) == 0):
            continue

        valid_sims += 1
        chi2_stat, p_val, dof, _ = stats.chi2_contingency(table)
        if p_val < alpha:
            rejections += 1

    sim_power = rejections / valid_sims if valid_sims > 0 else 0
    print(f"  Simulated power ({valid_sims:,} valid simulations): {sim_power:.4f}")

    return sim_power


def h3_power(n_tasks: int = 50, n_models: int = 4, alpha: float = 0.05):
    """
    H3: Model variation — pairwise two-proportion z-test.

    Power computed using Cohen's h (arcsine transformation).
    """
    print("\n" + "=" * 70)
    print("H3: Model variation (pairwise two-proportion z-test)")
    print("=" * 70)
    print(f"\n  Parameters: n={n_tasks} tasks per model, "
          f"{n_models} models, alpha={alpha}")

    def two_prop_power(p1, p2, n, alpha_level):
        """Power of two-sided two-proportion z-test via Cohen's h."""
        h = 2 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))
        z_crit = stats.norm.ppf(1 - alpha_level / 2)
        power = (stats.norm.cdf(abs(h) * np.sqrt(n / 2) - z_crit) +
                 stats.norm.cdf(-abs(h) * np.sqrt(n / 2) - z_crit))
        return power

    print(f"\n  Pairwise power (two-sided, alpha={alpha}):")
    print(f"  {'Model A rate':>13}  {'Model B rate':>13}  "
          f"{'Difference':>11}  {'Cohen h':>9}  {'Power':>8}")
    for rate_a, rate_b in [(0.10, 0.25), (0.10, 0.30), (0.15, 0.30),
                           (0.15, 0.35), (0.20, 0.35)]:
        h = 2 * (np.arcsin(np.sqrt(rate_a)) - np.arcsin(np.sqrt(rate_b)))
        pwr = two_prop_power(rate_a, rate_b, n_tasks, alpha)
        print(f"  {rate_a:>13.0%}  {rate_b:>13.0%}  "
              f"{abs(rate_b - rate_a):>11.0%}  {abs(h):>9.3f}  {pwr:>8.4f}")

    # Sample size for 80% power at 15pp difference (10% vs 25%)
    rate_a, rate_b = 0.10, 0.25
    for n_test in range(10, 500):
        pwr = two_prop_power(rate_a, rate_b, n_test, alpha)
        if pwr >= 0.80:
            print(f"\n  Tasks per model for 80% power "
                  f"({rate_a:.0%} vs {rate_b:.0%}): {n_test}")
            break

    # With Holm-Bonferroni correction
    n_comparisons = n_models * (n_models - 1) // 2
    alpha_corrected = alpha / n_comparisons
    print(f"\n  With Holm-Bonferroni correction "
          f"({n_comparisons} pairwise comparisons):")
    print(f"  Strictest adjusted alpha = {alpha_corrected:.4f}")
    print(f"  {'Model A rate':>13}  {'Model B rate':>13}  {'Power (corrected)':>18}")
    for rate_a, rate_b in [(0.10, 0.25), (0.10, 0.30), (0.15, 0.30)]:
        pwr = two_prop_power(rate_a, rate_b, n_tasks, alpha_corrected)
        print(f"  {rate_a:>13.0%}  {rate_b:>13.0%}  {pwr:>18.4f}")


def h4_power(n_sabotaged: int = 15, llm_detect_rate: float = 0.60,
             sast_detect_rate: float = 0.25, alpha: float = 0.05,
             n_sims: int = 10_000):
    """
    H4: LLM monitors detect sabotage better than SAST tools.
    McNemar's exact test on paired detection outcomes.
    """
    print("\n" + "=" * 70)
    print("H4: Monitor comparison (McNemar's exact test)")
    print("=" * 70)
    print(f"\n  Parameters: n_sabotaged_patches={n_sabotaged}, "
          f"LLM detection={llm_detect_rate:.0%}, "
          f"SAST detection={sast_detect_rate:.0%}, alpha={alpha}")

    np.random.seed(42)
    rejections = 0
    valid = 0

    for _ in range(n_sims):
        llm = np.random.binomial(1, llm_detect_rate, n_sabotaged)
        sast = np.random.binomial(1, sast_detect_rate, n_sabotaged)

        b = np.sum((llm == 1) & (sast == 0))
        c = np.sum((llm == 0) & (sast == 1))
        n_disc = b + c

        if n_disc == 0:
            continue
        valid += 1

        # Two-sided exact McNemar
        p_val = 2 * min(
            stats.binom.cdf(min(b, c), n_disc, 0.5),
            1 - stats.binom.cdf(max(b, c) - 1, n_disc, 0.5)
        )
        p_val = min(p_val, 1.0)

        if p_val < alpha:
            rejections += 1

    power = rejections / valid if valid > 0 else 0
    print(f"  Simulated power ({valid:,} valid simulations): {power:.4f}")

    print(f"\n  Power vs number of sabotaged patches "
          f"(LLM={llm_detect_rate:.0%}, SAST={sast_detect_rate:.0%}):")
    print(f"  {'n_sabotaged':>12}  {'Power':>8}")
    for n in [5, 10, 15, 20, 25, 30, 40, 50]:
        rejs = 0
        val = 0
        for _ in range(n_sims):
            l = np.random.binomial(1, llm_detect_rate, n)
            s = np.random.binomial(1, sast_detect_rate, n)
            b_s = np.sum((l == 1) & (s == 0))
            c_s = np.sum((l == 0) & (s == 1))
            nd = b_s + c_s
            if nd == 0:
                continue
            val += 1
            pv = 2 * min(
                stats.binom.cdf(min(b_s, c_s), nd, 0.5),
                1 - stats.binom.cdf(max(b_s, c_s) - 1, nd, 0.5)
            )
            pv = min(pv, 1.0)
            if pv < alpha:
                rejs += 1
        pwr = rejs / val if val > 0 else 0
        print(f"  {n:>12}  {pwr:>8.4f}")

    return power


def print_summary():
    """Print claims from the paper to check against outputs."""
    print("\n" + "=" * 70)
    print("VERIFICATION: Claims in Section 5.3 to check against output above")
    print("=" * 70)
    print("""
    Claim 1 (H1a): "With n=50, even 3 successes (6%) gives p < 0.001"
        -> Check p-value for k=3 under H0: p <= 0.01.
        -> Under strict H0: p=0, any k>=1 trivially rejects.

    Claim 2 (H1b): "McNemar's test with n=50 paired observations has ~85%
        power to detect [20% vs 5% difference]"
        -> Check simulated power for sabotage=20%, baseline=5%.

    Claim 3 (H2): "chi-squared test with 5 df has ~80% power to detect a
        medium effect size (w=0.3)"
        -> Check analytical power for w=0.3 with n=50 and df=5.

    Claim 4 (H3): "~80% power to detect a difference of 15 percentage points
        between two models"
        -> Check two-proportion z-test for 10% vs 25% with n=50.
    """)


if __name__ == "__main__":
    print("SWE-Sabotage Power Analysis")
    print("=" * 70)
    print()

    h1a_power(n_tasks=50, true_rate=0.20)
    h1b_power(n_tasks=50, sabotage_rate=0.20, baseline_rate=0.05)
    h2_power(n_tasks=50, n_classes=6)
    h3_power(n_tasks=50, n_models=4)
    h4_power(n_sabotaged=15, llm_detect_rate=0.60, sast_detect_rate=0.25)
    print_summary()
