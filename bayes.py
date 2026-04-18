"""
Bayesian analyses for game_ranking.

1. bayesian_D(scores, game_type)
   Conjugate Normal-Normal posterior on mu. Returns Bayesian D and posterior params.

2. cross_platform_comparison(scores_a, scores_b)
   P(mu_a > mu_b) and credible interval on (mu_a - mu_b).
   Analytically exact under Normal likelihood with known variance estimated from data.

3. hierarchical_shrinkage(puzzle_ds)
   Empirical Bayes partial pooling. Shrinks each puzzle's D toward the population mean,
   weighted by n. Low-n puzzles are pulled toward the group; high-n puzzles stay put.
"""

import numpy as np
import scipy.stats as st
import sqlite3
import game_ranking as gr


# ---------------------------------------------------------------------------
# 1. Bayesian D — conjugate Normal-Normal
# ---------------------------------------------------------------------------

def bayesian_D(scores, game_type, prior_mean=None, prior_var=None):
    """
    Conjugate Normal-Normal update on mu.

    Prior: mu ~ N(prior_mean, prior_var)
    Likelihood: scores ~ N(mu, sigma²)

    Returns dict with posterior params and Bayesian-adjusted D.
    If prior_mean is None, uses a weakly informative prior centered on the
    observed mean with large variance (equivalent to near-flat prior).
    """
    scores = np.array(scores, dtype=float)
    n = len(scores)
    if n == 0:
        return None

    xbar = scores.mean()
    sigma2 = scores.var() + 1e-6  # add epsilon to avoid zero variance

    # Weakly informative prior if not supplied
    if prior_mean is None:
        prior_mean = xbar
    if prior_var is None:
        prior_var = sigma2 * 100  # vague prior

    # Conjugate update
    post_var = 1.0 / (1.0 / prior_var + n / sigma2)
    post_mean = post_var * (prior_mean / prior_var + n * xbar / sigma2)
    post_std = np.sqrt(post_var)

    # Convergence: fractional change in posterior std relative to prior std
    convergence = 1.0 - post_std / np.sqrt(prior_var)

    # Recompute D using posterior mean instead of sample mean
    gamma = 1
    skew = st.skew(scores) if n > 1 else 0
    skew_factor = 1 + 0.01 * skew
    obs_var = scores.var() + gamma
    norm_var = np.sqrt(obs_var) / (post_mean + gamma)
    a = 1 if game_type == 'wordle' else 15
    b = 0.015

    if game_type == 'wordle':
        D = np.round((a * post_mean + b * norm_var) / skew_factor, 2)
    else:
        D = np.clip(np.round((a * (1 / (post_mean + gamma)) + b * norm_var) / skew_factor, 5) * 1000, 1, 10000)
        D = np.round(D, 2)

    return {
        'n': n,
        'xbar': round(float(xbar), 2),
        'post_mean': round(float(post_mean), 2),
        'post_std': round(float(post_std), 2),
        'convergence': round(float(convergence), 4),  # 0 = no info, 1 = fully converged
        'D': float(D),
    }


# ---------------------------------------------------------------------------
# 2. Cross-platform comparison
# ---------------------------------------------------------------------------

def cross_platform_comparison(scores_a, scores_b, label_a='a', label_b='b'):
    """
    Computes P(mu_a > mu_b) and 95% credible interval on (mu_a - mu_b).

    Uses Normal approximation: each platform's mean is N(xbar, sigma²/n).
    Difference of two independent normals is analytic.

    Returns dict with probability and credible interval.
    """
    scores_a = np.array(scores_a, dtype=float)
    scores_b = np.array(scores_b, dtype=float)

    if len(scores_a) < 2 or len(scores_b) < 2:
        return None

    mu_a, sigma2_a, n_a = scores_a.mean(), scores_a.var() + 1e-6, len(scores_a)
    mu_b, sigma2_b, n_b = scores_b.mean(), scores_b.var() + 1e-6, len(scores_b)

    # Sampling distribution of difference: (xbar_a - xbar_b) ~ N(mu_a-mu_b, se²)
    diff_mean = mu_a - mu_b
    diff_se = np.sqrt(sigma2_a / n_a + sigma2_b / n_b)

    # P(mu_a > mu_b) = P(diff > 0)
    p_a_greater = 1.0 - st.norm.cdf(0, loc=diff_mean, scale=diff_se)

    # 95% credible interval
    ci_lo = diff_mean - 1.96 * diff_se
    ci_hi = diff_mean + 1.96 * diff_se

    return {
        f'mean_{label_a}': round(float(mu_a), 2),
        f'mean_{label_b}': round(float(mu_b), 2),
        'diff_mean': round(float(diff_mean), 2),
        'diff_ci_95': (round(float(ci_lo), 2), round(float(ci_hi), 2)),
        f'p_{label_a}_greater': round(float(p_a_greater), 3),
        f'p_{label_b}_greater': round(float(1 - p_a_greater), 3),
    }


# ---------------------------------------------------------------------------
# 3. Hierarchical shrinkage — empirical Bayes
# ---------------------------------------------------------------------------

def hierarchical_shrinkage(puzzle_ds):
    """
    Empirical Bayes partial pooling on D values.

    puzzle_ds: list of (puzzle_number, D, n)

    Estimates population mean (mu_pop) and between-puzzle variance (tau²)
    from data. Shrinks each puzzle's D toward mu_pop:

        D_shrunk = lambda * D_obs + (1 - lambda) * mu_pop
        lambda = tau² / (tau² + sigma²/n)   where sigma² = within-puzzle variance

    Returns list of (puzzle_number, D_obs, D_shrunk, lambda, n).
    """
    if len(puzzle_ds) < 3:
        return [(p, d, d, 1.0, n) for p, d, n in puzzle_ds]

    ds = np.array([d for _, d, _ in puzzle_ds])
    ns = np.array([n for _, _, n in puzzle_ds])

    mu_pop = ds.mean()
    tau2 = max(ds.var() - (ds / (ns + 1e-6)).mean(), 1e-6)  # method of moments

    result = []
    for puzzle_number, D_obs, n in puzzle_ds:
        sigma2_n = D_obs / (n + 1e-6)  # rough within-puzzle uncertainty
        lam = tau2 / (tau2 + sigma2_n)
        D_shrunk = lam * D_obs + (1 - lam) * mu_pop
        result.append({
            'puzzle_number': puzzle_number,
            'D_obs': round(float(D_obs), 2),
            'D_shrunk': round(float(D_shrunk), 2),
            'lambda': round(float(lam), 3),
            'n': int(n),
        })

    return result


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_d_history(game_type, puzzle_number, platform):
    """Returns list of (n, D) ordered by n — D trajectory as scores accumulated."""
    conn = sqlite3.connect(gr.DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT n, D FROM d_history
        WHERE game_type = ? AND puzzle_number = ? AND platform = ?
        ORDER BY n ASC
    ''', (game_type, puzzle_number, platform))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_platform_scores(game_type, puzzle_number=None):
    """Returns {platform: [scores]} for a game, optionally filtered to one puzzle."""
    conn = sqlite3.connect(gr.DB_FILE)
    cursor = conn.cursor()
    if puzzle_number is not None:
        cursor.execute('''
            SELECT platform, score FROM puzzles
            WHERE game_type = ? AND puzzle_number = ?
        ''', (game_type, puzzle_number))
    else:
        cursor.execute('SELECT platform, score FROM puzzles WHERE game_type = ?', (game_type,))
    rows = cursor.fetchall()
    conn.close()
    by_platform = {}
    for platform, score in rows:
        by_platform.setdefault(platform, []).append(score)
    return by_platform


def get_all_rankings(game_type, platform):
    """Returns list of (puzzle_number, D, n) for empirical Bayes input."""
    conn = sqlite3.connect(gr.DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.puzzle_number, r.ranking, COUNT(p.id) as n
        FROM rankings r
        JOIN puzzles p ON p.game_type = r.game_type
                      AND p.puzzle_number = r.puzzle_number
                      AND p.platform = r.platform
        WHERE r.game_type = ? AND r.platform = ?
        GROUP BY r.puzzle_number
    ''', (game_type, platform))
    rows = cursor.fetchall()
    conn.close()
    return [(r[0], r[1], r[2]) for r in rows]
