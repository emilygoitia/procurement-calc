# Procurement_Calculator.py — v3 (all equipment in left editor, NaN-safe, holiday presets)
import streamlit as st
import pandas as pd
import numpy as np

# ---- Hard block if plotly isn't installed (so the message is clear on Cloud) ----
try:
    import plotly.express as px
except ModuleNotFoundError:
    st.error("Plotly isn’t installed on this deployment. Add `plotly==6.3.0` to requirements.txt (pinned) and Restart the app.")
    st.stop()

# ======================= Branding =======================
MANO_BLUE = "#1b6a87"
MANO_OFFWHITE = "#f4f6f6"
MANO_GREY = "#24333b"
FITOUT_COLOR = "#DECADE"   # requested color (hex but not standard; used sparingly)
SUPPORT_COLORS = ["#F34213", "#F6AE2D", "#8AAA79"]

BRAND_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700&display=swap');
:root {{
  --mano-blue: {MANO_BLUE};
  --mano-offwhite: {MANO_OFFWHITE};
  --mano-grey: {MANO_GREY};
}}
html, body, [class*="css"]  {{ font-family: 'Raleway', sans-serif; }}
.stApp {{ background: var(--mano-offwhite); }}
h1, h2, h3, h4, h5, h6 {{ color: var(--mano-grey); font-weight: 600; }}
.block-container {{ padding-top: 1.0rem; }}
section[data-testid="stSidebar"] > div {{ background: white; border-right: 4px solid var(--mano-blue); }}
.stButton>button, .stDownloadButton>button {{
  background: var(--mano-blue); color: white; border: 0; border-radius: 12px; padding: .5rem 1rem;
}}
.dataframe tbody tr:nth-child(even) {{ background: rgba(27,106,135,0.05); }}
.small-muted {{ color: #5c6b73; font-size: 0.875rem; }}
.kpi-card {{
  background: white; border-radius: 16px; padding: 16px;
  border-left: 6px solid var(--mano-blue); box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}}
</style>
"""

st.set_page_config(page_title="Mano Procurement Calculator", layout="wide")
st.markdown(BRAND_CSS, unsafe_allow_html=True)

# ======================= Defaults / Constants =======================
DEFAULT_SUBMITTAL_BDAYS = 15
DEFAULT_SHIPPING_BDAYS = 15
DEFAULT_BUFFER_BDAYS = 20

# Standard equipment library (no uploads). Manufacturing defaults to 0 so you can set per item.
STANDARD_EQUIPMENT = [
    {"Equipment": "Air Cooled Chiller",                   "Manufacturing (days)": 0},
    {"Equipment": "Computer Room Air Conditioner",        "Manufacturing (days)": 0},
    {"Equipment": "Fire Pump MV Transformer",             "Manufacturing (days)": 0},
    {"Equipment": "Fire Suppression System Generator",    "Manufacturing (days)": 0},
    {"Equipment": "Generator",                            "Manufacturing (days)": 0},
    {"Equipment": "House Generator",                      "Manufacturing (days)": 0},
    {"Equipment": "House Main Switchboard",               "Manufacturing (days)": 0},
    {"Equipment": "House Maintenance Bypass Board",       "Manufacturing (days)": 0},
    {"Equipment": "House Transformer",                    "Manufacturing (days)": 0},
    {"Equipment": "MV Switchgear",                        "Manufacturing (days)": 0},
    {"Equipment": "Main Switchboard",                     "Manufacturing (days)": 0},
    {"Equipment": "Maintenance Bypass Board",             "Manufacturing (days)": 0},
    {"Equipment": "Mechanical Panels",                    "Manufacturing (days)": 0},
    {"Equipment": "Modular Electrical Room",              "Manufacturing (days)": 0},
    {"Equipment": "Padmount Transformer",                 "Manufacturing (days)": 0},
    {"Equipment": "Power Distribution Unit",              "Manufacturing (days)": 0},
    {"Equipment": "Static Transfer Switch",               "Manufacturing (days)": 0},
    {"Equipment": "UPS Battery Cabinet",                  "Manufacturing (days)": 0},
    {"Equipment": "UPS Board",                            "Manufacturing (days)": 0},
    {"Equipment": "UPS Board Reserve",                    "Manufacturing (days)": 0},
    {"Equipment": "Uninterruptible Power Supply",         "Manufacturing (days)": 0},
    {"Equipment": "Uninterruptible Power Supply (House)", "Manufacturing (days)": 0},
]

# ======================= Helpers =======================
def as_int(x, default=0):
    """Convert to int safely; treat NaN/None/'' as default."""
    try:
        if pd.isna(x) or x == "":
            return default
        return int(float(x))
    except Exception:
        return default

def bday_add(start_date: pd.Timestamp, days: int, holidays: set | None = None) -> pd.Timestamp:
    """Add business days (Mon–Fri), skipping holidays."""
    if pd.isna(start_date) or days is None:
        return pd.NaT
    holidays = holidays or set()
    return pd.to_datetime(
        np.busday_offset(np.datetime64(pd.to_datetime(start_date).date()), days, holidays=sorted(list(holidays)))
    )

def bday_sub(end_date: pd.Timestamp, days: int, holidays: set | None = None) -> pd.Timestamp:
    """Subtract business days (Mon–Fri), skipping holidays."""
    if pd.isna(end_date) or days is None:
        return pd.NaT
    holidays = holidays or set()
    return pd.to_datetime(
        np.busday_offset(np.datetime64(pd.to_datetime(end_date).date()), -days, holidays=sorted(list(holidays)))
    )

def compute_pass(row: pd.Series, mode: str, holidays: set | None = None) -> dict:
    """
    mode: 'Forward' (PO -> ROJ) or 'Backward' (ROJ -> PO)
    Returns dict of key dates for Gantt and table.
    """
    sub  = as_int(row.get("Submittal (bdays)", DEFAULT_SUBMITTAL_BDAYS), DEFAULT_SUBMITTAL_BDAYS)
    mfg  = as_int(row.get("Manufacturing (days)", 0), 0)
    ship = as_int(row.get("Shipping (bdays)", DEFAULT_SHIPPING_BDAYS), DEFAULT_SHIPPING_BDAYS)
    buf  = as_int(row.get("Buffer (bdays)", DEFAULT_BUFFER_BDAYS), DEFAULT_BUFFER_BDAYS)

    po  = pd.to_datetime(row.get("PO Execution")) if "PO Execution" in row else pd.NaT
    roj = pd.to_datetime(row.get("ROJ")) if "ROJ" in row else pd.NaT

    # Treat manufacturing as business days to align with other durations.
    mfg_bdays = int(mfg)

    if mode == "Forward":
        if pd.isna(po):
            return {}
        sub_end = bday_add(po, sub, holidays)
        mfg_end = bday_add(sub_end, mfg_bdays, holidays)
        ship_end = bday_add(mfg_end, ship, holidays)
        roj_calc = bday_add(ship_end, buf, holidays)
        return {
            "PO Execution": po,
            "Submittal Start": po,
            "Submittal End": sub_end,
            "Manufacturing Start": sub_end,
            "Manufacturing End": mfg_end,
            "Shipping Start": mfg_end,
            "Shipping End": ship_end,
            "Buffer Start": ship_end,
            "ROJ": roj_calc,
            "Buffer End": roj_calc,
        }
    else:  # Backward
        if pd.isna(roj):
            return {}
        ship_end = bday_sub(roj, buf, holidays)
        mfg_end  = bday_sub(ship_end, ship, holidays)
        sub_end  = bday_sub(mfg_end, mfg_bdays, holidays)
        po_calc  = bday_sub(sub_end, sub, holidays)
        return {
            "PO Execution": po_calc,
            "Submittal Start": po_calc,
            "Submittal End": sub_end,
            "Manufacturing Start": sub_end,
            "Manufacturing End": mfg_end,
            "Shipping Start": mfg_end,
            "Shipping End": ship_end,
            "Buffer Start": ship_end,
            "ROJ": roj,
            "Buffer End": roj,
        }

# ======================= UI =======================
st.title("Mano Procurement Calculator")

with st.sidebar:
    st.subheader("Settings")
    mode = st.radio("Pass Mode", ["Forward", "Backward"], help="Forward: PO → ROJ. Backward: ROJ → PO.")

    st.markdown("---")
    st.caption("**Holiday Calendar**")

    def build_calendar(name: str):
        """Return a list of holiday date strings for quick insert."""
        if name == "US Federal":
            try:
                from pandas.tseries.holiday import USFederalHolidayCalendar
                cal = USFederalHolidayCalendar()
                hol = cal.holidays(start="2025-01-01", end="2027-12-31").strftime("%Y-%m-%d").tolist()
                return hol
            except Exception:
                return []
        if name == "Spain (National + C. Valenciana)":
            # Representative sample; adjust as needed
            approx = [
                # 2025
                "2025-01-01", "2025-01-06", "2025-03-19", "2025-04-18", "2025-05-01", "2025-08-15",
                "2025-10-09", "2025-10-12", "2025-11-01", "2025-12-06", "2025-12-08", "2025-12-25",
                # 2026
                "2026-01-01", "2026-01-06", "2026-03-19", "2026-04-03", "2026-05-01", "2026-08-15",
                "2026-10-09", "2026-10-12", "2026-11-01", "2026-12-06", "2026-12-08", "2026-12-25",
            ]
            return approx
        return []

    calendar_choice = st.selectbox(
        "Preset Calendar",
        ["None", "US Federal", "Spain (National + C. Valenciana)"]
    )

    default_holidays_txt = "\n".join(build_calendar(calendar_choice)) if calendar_choice != "None" else ""
    holidays_text = st.text_area(
        "Holidays (editable)",
        value=default_holidays_txt,
        height=140,
        placeholder="YYYY-MM-DD one per line",
    )

    st.markdown("---")
    st.caption("**Defaults for New Rows (business days)**")
    def_sub = st.number_input("Default Submittal", value=DEFAULT_SUBMITTAL_BDAYS, min_value=0, step=1)
    def_ship = st.number_input("Default Shipping", value=DEFAULT_SHIPPING_BDAYS, min_value=0, step=1)
    def_buf = st.number_input("Default Buffer", value=DEFAULT_BUFFER_BDAYS, min_value=0, step=1)

# Initialize working table (always show ALL standard equipment)
base_df = pd.DataFrame(STANDARD_EQUIPMENT)

if "work_df" not in st.session_state or st.session_state.work_df is None:
    st.session_state.work_df = base_df.copy()
else:
    # Keep any custom rows (names not in standard list), then append full standard and dedup
    std_names = set(base_df["Equipment"])
    current = st.session_state.work_df.copy()
    if "Equipment" not in current.columns:
        current["Equipment"] = ""
    custom = current[~current["Equipment"].isin(std_names)] if not current.empty else pd.DataFrame(columns=["Equipment","Manufacturing (days)"])
    st.session_state.work_df = pd.concat([base_df, custom], ignore_index=True).drop_duplicates(subset=["Equipment"], keep="first")

# Normalize/ensure editor columns
editor_cols = [
    "Equipment",
    "PO Execution",
    "ROJ",
    "Submittal (bdays)",
    "Manufacturing (days)",
    "Shipping (bdays)",
    "Buffer (bdays)",
]
for c in editor_cols:
    if c not in st.session_state.work_df.columns:
        if c == "Equipment":
            continue
        elif c == "Manufacturing (days)":
            st.session_state.work_df[c] = 0
        elif c == "Submittal (bdays)":
            st.session_state.work_df[c] = DEFAULT_SUBMITTAL_BDAYS
        elif c == "Shipping (bdays)":
            st.session_state.work_df[c] = DEFAULT_SHIPPING_BDAYS
        elif c == "Buffer (bdays)":
            st.session_state.work_df[c] = DEFAULT_BUFFER_BDAYS
        else:
            st.session_state.work_df[c] = None

# Order columns and coerce numbers safely
st.session_state.work_df = st.session_state.work_df[editor_cols]
st.session_state.work_df["Manufacturing (days)"] = pd.to_numeric(
    st.session_state.work_df["Manufacturing (days)"], errors="coerce"
).fillna(0).astype(int)

st.markdown("### Equipment & Durations (edit here)")
edited_df = st.data_editor(
    st.session_state.work_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "PO Execution": st.column_config.DateColumn("PO Execution"),
        "ROJ": st.column_config.DateColumn("ROJ"),
        "Submittal (bdays)": st.column_config.NumberColumn(min_value=0, step=1),
        "Manufacturing (days)": st.column_config.NumberColumn(min_value=0, step=1),
        "Shipping (bdays)": st.column_config.NumberColumn(min_value=0, step=1),
        "Buffer (bdays)": st.column_config.NumberColumn(min_value=0, step=1),
    },
    hide_index=True,
)
st.session_state.work_df = edited_df.copy()

# Parse holidays
holiday_set = set()
for line in holidays_text.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        holiday_set.add(pd.to_datetime(line).date())
    except Exception:
        st.warning(f"Holiday date could not be parsed: {line}")

# ======================= Compute =======================
def compute_all(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        res = compute_pass(row, mode, holidays=holiday_set)
        if not res:
            continue
        rec = {"Equipment": row.get("Equipment", "")}
        rec.update(res)
        rec.update({
            "Submittal (bdays)": row.get("Submittal (bdays)", DEFAULT_SUBMITTAL_BDAYS),
            "Manufacturing (days)": row.get("Manufacturing (days)", 0),
            "Shipping (bdays)": row.get("Shipping (bdays)", DEFAULT_SHIPPING_BDAYS),
            "Buffer (bdays)": row.get("Buffer (bdays)", DEFAULT_BUFFER_BDAYS),
        })
        records.append(rec)
    if not records:
        return pd.DataFrame()
    out = pd.DataFrame(records)
    table_cols = [
        "Equipment",
        "PO Execution",
        "Submittal (bdays)",
        "Submittal Start",
        "Submittal End",
        "Manufacturing (days)",
        "Manufacturing Start",
        "Manufacturing End",
        "Shipping (bdays)",
        "Shipping Start",
        "Shipping End",
        "Buffer (bdays)",
        "Buffer Start",
        "ROJ",
    ]
    return out[table_cols]

results_df = compute_all(st.session_state.work_df, mode)

# ======================= Output: Table =======================
st.markdown("### Calculated Dates")
if results_df.empty:
    st.info("Enter either PO Execution (Forward) or ROJ (Backward) for each row to calculate the chain.")
else:
    show_df = results_df.copy()
    for c in show_df.columns:
        if "Start" in c or "End" in c or c in {"PO Execution", "ROJ"}:
            show_df[c] = pd.to_datetime(show_df[c]).dt.date
    st.dataframe(show_df, use_container_width=True)

    csv = show_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Results (CSV)", data=csv, file_name="procurement_pass_results.csv", mime="text/csv")

# ======================= Output: Gantt =======================
st.markdown("### Timeline (per Equipment)")
if not results_df.empty:
    bars = []
    phase_order = [
        ("Submittal", "Submittal Start", "Submittal End"),
        ("Manufacturing", "Manufacturing Start", "Manufacturing End"),
        ("Shipping", "Shipping Start", "Shipping End"),
        ("Buffer", "Buffer Start", "ROJ"),
    ]
    for _, r in results_df.iterrows():
        for phase, s_col, e_col in phase_order:
            s = r.get(s_col)
            e = r.get(e_col)
            if pd.isna(s) or pd.isna(e):
                continue
            bars.append({
                "Equipment": r["Equipment"],
                "Phase": phase,
                "Start": pd.to_datetime(s),
                "Finish": pd.to_datetime(e),
            })
    if bars:
        gantt_df = pd.DataFrame(bars)
        fig = px.timeline(
            gantt_df,
            x_start="Start",
            x_end="Finish",
            y="Equipment",
            color="Phase",
            category_orders={"Phase": ["Submittal", "Manufacturing", "Shipping", "Buffer"]},
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=520, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline bars yet — enter dates to calculate first.")

# ======================= Notes =======================
st.markdown(
    """
<div class="small-muted">
<b>Assumptions:</b> Business-day math (Mon–Fri). Choose a preset holiday calendar or paste your own.
Manufacturing durations are treated as business days to match other phases; if your standards are calendar days, change <code>mfg_bdays</code> in <code>compute_pass()</code>.
<br>
<b>Workflow:</b> Forward pass computes ROJ from PO; backward pass computes PO from ROJ by subtracting durations. Edit durations and dates directly in the left table.
</div>
""",
    unsafe_allow_html=True,
)

