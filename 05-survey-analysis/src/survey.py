"""Small survey-statistics toolkit (weighted estimates with design-based standard errors).

The GSS is a stratified, clustered sample. Point estimates use the survey weight; standard errors use
Taylor linearisation with the variance strata (VSTRAT) and primary sampling units (VPSU), the same method as
Stata's `svy` or R's `survey` package (with-replacement approximation).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _design_var(z: np.ndarray, strata: np.ndarray, psu: np.ndarray) -> float:
    """Variance of a total of linearised values z under a stratified cluster design."""
    df = pd.DataFrame({"z": z, "h": strata, "c": psu})
    tot = df.groupby(["h", "c"])["z"].sum().reset_index()
    var = 0.0
    for _, g in tot.groupby("h"):
        n_h = len(g)
        if n_h > 1:
            var += n_h / (n_h - 1) * ((g["z"] - g["z"].mean()) ** 2).sum()
    return var


def proportion(y: pd.Series, w: pd.Series, strata: pd.Series, psu: pd.Series, conf: float = 0.95) -> dict:
    """Weighted proportion of y == 1 with a design-based CI (logit-transformed, so it stays in 0-1)."""
    m = y.notna() & w.notna()
    y, w, h, c = y[m].astype(float).values, w[m].values, strata[m].values, psu[m].values
    p = np.sum(w * y) / np.sum(w)
    z = w * (y - p) / np.sum(w)
    se = np.sqrt(_design_var(z, h, c))
    n_strata = len(np.unique(h))
    dof = len(np.unique(np.char.add(h.astype(str), c.astype(str)))) - n_strata
    t = stats.t.ppf(0.5 + conf / 2, dof)
    if 0 < p < 1:
        lp, se_l = np.log(p / (1 - p)), se / (p * (1 - p))
        lo, hi = 1 / (1 + np.exp(-(lp - t * se_l))), 1 / (1 + np.exp(-(lp + t * se_l)))
    else:
        lo = hi = p
    deff = se ** 2 / (p * (1 - p) / len(y)) if 0 < p < 1 else np.nan
    return {"p": p, "se": se, "lo": lo, "hi": hi, "n": int(len(y)), "deff": deff}


def proportions_by(df: pd.DataFrame, outcome: str, level, by: str, w: str, strata: str, psu: str) -> pd.DataFrame:
    """Share of `outcome == level` within each group of `by`, with 95% CIs.

    Domain estimation: the whole design is kept and the outcome is zero outside the domain, so the
    standard errors stay correct for subgroups.
    """
    rows = []
    d = df[df[outcome].notna()]
    for g in [x for x in d[by].dropna().unique()]:
        in_g = (d[by] == g).astype(float)
        y = (d[outcome] == level).astype(float) * in_g
        wy, wg = d[w] * y, d[w] * in_g
        p = wy.sum() / wg.sum()
        z = (d[w] * in_g * ((d[outcome] == level).astype(float) - p)) / wg.sum()
        se = np.sqrt(_design_var(z.values, d[strata].values, d[psu].values))
        lp, se_l = np.log(p / (1 - p)), se / (p * (1 - p))
        t = stats.t.ppf(0.975, d.groupby([strata, psu]).ngroups - d[strata].nunique())
        rows.append({by: g, "share": p, "lo": 1 / (1 + np.exp(-(lp - t * se_l))),
                     "hi": 1 / (1 + np.exp(-(lp + t * se_l))), "n": int(in_g.sum())})
    return pd.DataFrame(rows)


def weighted_crosstab(df: pd.DataFrame, row: str, col: str, w: str) -> pd.DataFrame:
    """Row percentages (weighted)."""
    t = df.pivot_table(index=row, columns=col, values=w, aggfunc="sum", observed=False).fillna(0)
    return t.div(t.sum(axis=1), axis=0) * 100


def chi_square(df: pd.DataFrame, row: str, col: str) -> dict:
    """Pearson chi-square test of independence on the unweighted counts, with Cramér's V and the
    smallest expected count (assumption check: expected counts of at least 5)."""
    tab = pd.crosstab(df[row], df[col])
    chi2, p, dof, expected = stats.chi2_contingency(tab, correction=False)
    n = tab.values.sum()
    v = np.sqrt(chi2 / (n * (min(tab.shape) - 1)))
    return {"chi2": chi2, "dof": dof, "p": p, "cramers_v": v, "min_expected": expected.min(),
            "cells_below_5": int((expected < 5).sum()), "n": int(n)}


def fmt_p(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"
