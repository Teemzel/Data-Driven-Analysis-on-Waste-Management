import os
from pathlib import Path
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- paths
BASE = Path(__file__).resolve().parent
STATE_FILE = "State Level OFMSW Amounts Generated - Nigeria.xlsx"
DATA = Path(os.environ.get("WASTE_DATA", BASE / "Data"))
if not (DATA / STATE_FILE).exists() and (BASE / STATE_FILE).exists():
    DATA = BASE                                   # script and data in the same folder
OUT = Path(os.environ.get("WASTE_OUT", BASE / "Output"))

# ----------------------------------------------------------------------------- inputs
YEARS = list(range(2023, 2036))

# UN World Population Prospects 2024, medium variant, mid-year population.
# Sources: worldometers.info (2023-26, 2030, 2035) and statisticstimes.com (2027-2035).
POP = dict(zip(YEARS, [227882945, 232679478, 237527782, 242431832, 247374263, 252346128, 257352638,
                       262380970, 267421074, 272483642, 277555115, 282622397, 287685763]))

# UN urban share (%): published for 2023-26, 2030 and 2035 (worldometers.info).
# 2027-29 and 2031-34 are LINEAR INTERPOLATIONS.
URB_PUBLISHED = {2023: 53.0, 2024: 53.9, 2025: 54.9, 2026: 55.8, 2030: 59.6, 2035: 64.3}
URB = pd.Series(URB_PUBLISHED).reindex(YEARS).interpolate(method="index").to_dict()

# World Bank national MSW (What a Waste 2.0, via Africa Check 2019): used ONLY to calibrate epsilon.
WB = dict(msw_2016_mt=34.6, msw_2030_mt=54.8, pop_2016_wb=186e6, pop_2016_un=195_443_700)

PARAMS = dict(
    baseline_scale=1.00,      # kappa. 1.00 = state file as is; calibrate()['wb_scale'] (about 1.585) matches the World Bank level
    elasticity_high=1.0,      # High scenario: per-capita waste grows as fast as the urban share
    composition_shift=1,      # 1 = organic share falls as per-capita waste rises (cross-state slope); 0 = fixed shares
)

# ----------------------------------------------------------------------------- data
def load_states(path=None):
    """Read the state file, drop the national total row, rename FCT, compute 2023 generation (t/yr)."""
    path = path or (DATA / STATE_FILE)
    d = pd.read_excel(path).iloc[:, :7]
    d.columns = ["State", "pc", "Pop_2006", "org_pct", "Pop_2023", "msw_file", "org_file"]
    d = d[d.State != "Federal Republic of Nigeria"].copy()
    d["State"] = d.State.replace({"FCT": "Federal Capital Territory"})
    d["gen0"] = d.pc * d.Pop_2023 * 365 / 1000            # t/yr = kg/person/day x persons x 365 / 1000
    return d.reset_index(drop=True)

def calibrate():
    """Elasticity of per-capita waste to urban share, from the World Bank 2016-2030 projection."""
    pc30 = WB["msw_2030_mt"] * 1e9 / 365 / POP[2030]                       # kg/person/day in 2030
    g = [((pc30 / (WB["msw_2016_mt"] * 1e9 / 365 / p16)) ** (1 / 14) - 1)   # per-capita growth per year
         for p16 in (WB["pop_2016_wb"], WB["pop_2016_un"])]
    g_mean = float(np.mean(g))
    urb_cagr = (URB[2030] / URB[2023]) ** (1 / 7) - 1                       # urban-share growth per year, 2023-2030
    wb_2023 = WB["msw_2016_mt"] * (WB["msw_2030_mt"] / WB["msw_2016_mt"]) ** (7 / 14)   # log-linear interpolation
    return dict(g_low=g[0], g_high=g[1], g_mean=g_mean, urb_cagr=urb_cagr,
                elasticity=g_mean / urb_cagr, wb_2023_mt=wb_2023)

# ----------------------------------------------------------------------------- model
def run_model(states=None, params=None):
    p = dict(PARAMS, **(params or {}))
    st = states if states is not None else load_states()
    cal = calibrate()
    cal["wb_scale"] = cal["wb_2023_mt"] / (st.gen0.sum() / 1e6)            # kappa that would match the World Bank level
    elas = {"Low": 0.0, "Central": cal["elasticity"], "High": p["elasticity_high"]}
    beta = float(np.polyfit(st.pc, st.org_pct, 1)[0])                       # pp of organic share per +1 kg/person/day
    r = float(np.corrcoef(st.pc, st.org_pct)[0, 1])
    popidx = {t: POP[t] / POP[2023] for t in YEARS}
    urbidx = {t: URB[t] / URB[2023] for t in YEARS}

    state_rows, nat_rows = [], []
    for scen, e in elas.items():
        for t in YEARS:
            m = urbidx[t] ** e                                              # per-capita multiplier M(t)
            gen = st.gen0 * popidx[t] * m * p["baseline_scale"]             # equation (1)
            org_pct = st.org_pct + p["composition_shift"] * beta * st.pc * (m - 1)   # equation (3)
            org = gen * org_pct / 100                                       # equation (4)
            for i in range(len(st)):
                state_rows.append(dict(State=st.State[i], scenario=scen, year=t, multiplier=m,
                                       generation_t=gen[i], organic_pct=org_pct[i], organic_t=org[i]))
            G, O = gen.sum(), org.sum()
            nat_rows.append(dict(scenario=scen, year=t, multiplier=m, generation_t=G, organic_t=O,
                                 organic_share_pct=100 * O / G,
                                 per_capita_kg_day=G * 1000 / (st.Pop_2023.sum() * popidx[t] * 365),
                                 generation_index=G / (st.gen0.sum() * p["baseline_scale"])))
    return dict(cal=cal, beta=beta, r=r, elas=elas, params=p, states=st,
                state_df=pd.DataFrame(state_rows), nat_df=pd.DataFrame(nat_rows))

# ----------------------------------------------------------------------------- outputs
def make_outputs(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    OUT.mkdir(parents=True, exist_ok=True)
    nat = res["nat_df"]
    nat.to_csv(OUT / "national_projection_2023_2035.csv", index=False)
    res["state_df"].to_csv(OUT / "state_projection_2023_2035.csv", index=False)

    col = {"Low": "#2E75B6", "Central": "#C55A11", "High": "#7F7F7F"}
    plt.rcParams.update({"font.size": 9})
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.8))
    for scen in ("Low", "Central", "High"):
        x = nat[nat.scenario == scen]
        style = dict(color=col[scen], lw=2.2 if scen == "Central" else 1.6, ls="-" if scen == "Central" else "--")
        ax[0].plot(x.year, x.generation_t / 1e6, label=f"{scen} (per-capita elasticity {res['elas'][scen]:.2f})", **style)
        ax[1].plot(x.year, x.organic_share_pct, label=scen, **style)
    lo, hi = nat[nat.scenario == "Low"], nat[nat.scenario == "High"]
    ax[0].fill_between(YEARS, lo.generation_t / 1e6, hi.generation_t / 1e6, color="#F4B183", alpha=.3)
    ax[0].scatter([2030], [WB["msw_2030_mt"]], marker="D", facecolor="white", edgecolor="black", zorder=5,
                  label="World Bank 2030 projection (different baseline)")
    ax[0].set_title("National MSW generation (state-file baseline)", loc="left", fontweight="bold")
    ax[0].set_ylabel("Million tonnes / year"); ax[0].set_ylim(0, 60); ax[0].legend(frameon=False, fontsize=8, loc="lower right")
    ax[1].set_title("Organic share of national waste", loc="left", fontweight="bold")
    ax[1].set_ylabel("%"); ax[1].set_ylim(45, 62)       # note: axis starts at 45%; set (0, 100) for an unexaggerated view
    ax[1].legend(frameon=False)
    for a in ax: a.grid(alpha=.25)
    plt.tight_layout(); plt.savefig(OUT / "projection_generation.png", dpi=150); plt.close()

if __name__ == "__main__":
    res = run_model()
    make_outputs(res)
    nat, cal = res["nat_df"], res["cal"]

    # internal check: the sum of the state rows must equal the national row
    chk = res["state_df"].groupby(["scenario", "year"]).generation_t.sum().reset_index().merge(nat, on=["scenario", "year"])
    assert np.allclose(chk.generation_t_x, chk.generation_t_y), "state rows do not add up to national totals"

    print(f"Calibration: per-capita growth {cal['g_low']:.2%} to {cal['g_high']:.2%} per year (mean {cal['g_mean']:.2%}); "
          f"urban-share growth {cal['urb_cagr']:.2%} per year -> central elasticity {cal['elasticity']:.3f}")
    print(f"Organic share vs per-capita slope: {res['beta']:.1f} points per kg/person/day (r = {res['r']:.2f})")
    print(f"State-file total 2023: {nat[(nat.scenario == 'Central') & (nat.year == 2023)].generation_t.iloc[0] / 1e6:.2f} Mt; "
          f"World Bank-interpolated 2023: {cal['wb_2023_mt']:.1f} Mt (scaling factor {cal['wb_scale']:.3f})\n")
    show = nat[nat.year.isin([2023, 2026, 2030, 2035])].copy()
    show["generation_Mt"] = (show.generation_t / 1e6).round(2); show["organic_Mt"] = (show.organic_t / 1e6).round(2)
    show["organic_share_pct"] = show.organic_share_pct.round(1); show["per_capita_kg_day"] = show.per_capita_kg_day.round(3)
    print(show[["scenario", "year", "generation_Mt", "per_capita_kg_day", "organic_share_pct", "organic_Mt"]].to_string(index=False))
    print("\nOutputs written to", OUT)