# Procurement_Calculator.py — v6.1
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

# ---- Plotly guard ----
try:
    import plotly.express as px
except ModuleNotFoundError:
    st.error("Plotly isn’t installed. Run: pip install streamlit pandas numpy plotly")
    st.stop()

# ================= Branding =================
MANO_BLUE = "#1b6a87"
MANO_OFFWHITE = "#f4f6f6"
MANO_GREY = "#24333b"

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
/* Mano-blue focus outline on editable cells */
.stDataFrame [data-testid="stDataFrameCell"]:focus {{
  outline: 2px solid {MANO_BLUE} !important;
}}
.small-muted {{ color: #5c6b73; font-size: 0.875rem; }}
</style>
"""
st.set_page_config(page_title="Procurement Calculator", layout="wide")
st.markdown(BRAND_CSS, unsafe_allow_html=True)

# ============ Defaults & Equipment ============
DEFAULT_SUBMITTAL_DAYS = 15
DEFAULT_SHIPPING_DAYS = 15
DEFAULT_BUFFER_DAYS = 20
TODAY = pd.to_datetime(date.today())

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

# ============ Helpers ============
def as_int(x, default=0):
    try:
        if pd.isna(x) or x == "":
            return default
        return int(float(x))
    except Exception:
        return default

def bday_add(start, days, holidays=None):
    if pd.isna(start) or days is None: return pd.NaT
    return pd.to_datetime(np.busday_offset(np.datetime64(pd.to_datetime(start).date()), days,
                                           holidays=sorted(list(holidays or set()))))

def bday_sub(end, days, holidays=None):
    if pd.isna(end) or days is None: return pd.NaT
    return pd.to_datetime(np.busday_offset(np.datetime64(pd.to_datetime(end).date()), -days,
                                           holidays=sorted(list(holidays or set()))))

def bday_diff(d1, d2, holidays):
    if pd.isna(d1) or pd.isna(d2): return None
    return int(np.busday_count(np.datetime64(pd.to_datetime(d1).date()),
                               np.datetime64(pd.to_datetime(d2).date()),
                               holidays=sorted(list(holidays or set()))))

def compute_pass(row, mode, holidays=None):
    sub  = as_int(row.get("Submittal (days)", DEFAULT_SUBMITTAL_DAYS), DEFAULT_SUBMITTAL_DAYS)
    mfg  = as_int(row.get("Manufacturing (days)", 0), 0)
    ship = as_int(row.get("Shipping (days)",  DEFAULT_SHIPPING_DAYS),  DEFAULT_SHIPPING_DAYS)
    buf  = as_int(row.get("Buffer (days)",    DEFAULT_BUFFER_DAYS),    DEFAULT_BUFFER_DAYS)
    po, roj = pd.to_datetime(row.get("PO Execution")), pd.to_datetime(row.get("ROJ"))

    if mode == "Forward":
        if pd.isna(po): return {}
        sub_end = bday_add(po, sub, holidays)
        mfg_end = bday_add(sub_end, mfg, holidays)
        ship_end = bday_add(mfg_end, ship, holidays)
        roj_calc = bday_add(ship_end, buf, holidays)
        return {"PO Execution": po, "Submittal Start": po, "Submittal End": sub_end,
                "Manufacturing Start": sub_end, "Manufacturing End": mfg_end,
                "Shipping Start": mfg_end, "Shipping End": ship_end,
                "Buffer Start": ship_end, "ROJ": roj_calc, "Buffer End": roj_calc}
    elif mode == "Backward":
        if pd.isna(roj): return {}
        ship_end = bday_sub(roj, buf, holidays)
        mfg_end  = bday_sub(ship_end, ship, holidays)
        sub_end  = bday_sub(mfg_end, mfg, holidays)
        po_calc  = bday_sub(sub_end, sub, holidays)
        return {"PO Execution": po_calc, "Submittal Start": po_calc, "Submittal End": sub_end,
                "Manufacturing Start": sub_end, "Manufacturing End": mfg_end,
                "Shipping Start": mfg_end, "Shipping End": ship_end,
                "Buffer Start": ship_end, "ROJ": roj, "Buffer End": roj}
    else:
        return {}

# ============ UI: Title & Notes ============
st.title("Procurement Calculator")
st.subheader("Assumptions & Notes")
st.markdown(
    """
<div class="small-muted">
<b>Assumptions:</b> Business-day math (Mon–Fri). Choose a single holiday preset.<br>
<b>Per-row Mode:</b> Forward = compute ROJ from PO. Backward = compute PO from ROJ.<br>
<b>Float:</b> Negative means past-due. Positive means available buffer.<br>
</div>
""",
    unsafe_allow_html=True,
)

# ============ Sidebar: Holiday presets ============
with st.sidebar:
    st.subheader("Holiday Calendar")

    def build_calendar(name: str):
        if name == "US Federal":
            try:
                from pandas.tseries.holiday import USFederalHolidayCalendar
                cal = USFederalHolidayCalendar()
                return set(pd.to_datetime(cal.holidays(start="2025-01-01", end="2027-12-31")).date)
            except Exception:
                return set()
        if name == "Spain (C. Valenciana)":
            return set(pd.to_datetime([
                "2025-01-01","2025-01-06","2025-03-19","2025-04-18","2025-05-01","2025-08-15",
                "2025-10-09","2025-10-12","2025-11-01","2025-12-06","2025-12-08","2025-12-25",
                "2026-01-01","2026-01-06","2026-03-19","2026-04-03","2026-05-01","2026-08-15",
                "2026-10-09","2026-10-12","2026-11-01","2026-12-06","2026-12-08","2026-12-25",
            ]).date)
        if name == "Netherlands":
            return set(pd.to_datetime([
                "2025-01-01","2025-04-18","2025-04-20","2025-04-21","2025-04-26","2025-05-05","2025-05-29","2025-06-09","2025-12-25","2025-12-26",
                "2026-01-01","2026-04-03","2026-04-05","2026-04-06","2026-04-27","2026-05-05","2026-05-14","2026-05-25","2026-12-25","2026-12-26",
            ]).date)
        if name == "Italy":
            return set(pd.to_datetime([
                "2025-01-01","2025-01-06","2025-04-20","2025-04-21","2025-04-25","2025-05-01","2025-06-02","2025-08-15","2025-11-01","2025-12-08","2025-12-25","2025-12-26",
                "2026-01-01","2026-01-06","2026-04-05","2026-04-06","2026-04-25","2026-05-01","2026-06-02","2026-08-15","2026-11-01","2026-12-08","2026-12-25","2026-12-26",
            ]).date)
        if name == "UK (England & Wales)":
            return set(pd.to_datetime([
                "2025-01-01","2025-04-18","2025-04-21","2025-05-05","2025-05-26","2025-08-25","2025-12-25","2025-12-26",
                "2026-01-01","2026-04-03","2026-04-06","2026-05-04","2026-05-25","2026-08-31","2026-12-25","2026-12-28",
            ]).date)
        if name == "Mexico":
            return set(pd.to_datetime([
                "2025-01-01","2025-02-03","2025-03-17","2025-05-01","2025-09-16","2025-11-17","2025-12-25",
                "2026-01-01","2026-02-02","2026-03-16","2026-05-01","2026-09-16","2026-11-16","2026-12-25",
            ]).date)
        return set()

    calendar_choice = st.selectbox(
        "Preset",
        ["None", "US Federal", "Spain (C. Valenciana)", "Netherlands", "Italy", "UK (England & Wales)", "Mexico"]
    )
    holiday_set = build_calendar(calendar_choice)

# ============ Buttons (Clear / Reset) ============
c1, c2 = st.columns([1, 1])
with c1:
    if st.button("Clear All Inputs"):
        # Keep equipment names; clear dates & durations back to defaults
        base = pd.DataFrame(STANDARD_EQUIPMENT).copy()
        base["Mode"] = ""
        base["ROJ"] = pd.NaT
        base["PO Execution"] = pd.NaT
        base["Submittal (days)"] = DEFAULT_SUBMITTAL_DAYS
        base["Shipping (days)"] = DEFAULT_SHIPPING_DAYS
        base["Buffer (days)"] = DEFAULT_BUFFER_DAYS
        st.session_state.work_df = base.copy()
with c2:
    if st.button("Reset Default Equipment"):
        st.session_state.work_df = pd.DataFrame(STANDARD_EQUIPMENT).copy()

# ============ Data & Editor ============
# Initialize session data
if "work_df" not in st.session_state or st.session_state.work_df is None:
    st.session_state.work_df = pd.DataFrame(STANDARD_EQUIPMENT).copy()

# Ensure full standard list remains present (keep any custom items if later added)
std_names = set(pd.DataFrame(STANDARD_EQUIPMENT)["Equipment"])
current = st.session_state.work_df.copy()
if "Equipment" not in current.columns:
    current["Equipment"] = ""
custom = current[~current["Equipment"].isin(std_names)] if not current.empty else pd.DataFrame(columns=["Equipment","Manufacturing (days)"])
base_df = pd.DataFrame(STANDARD_EQUIPMENT)
work_df = pd.concat([base_df, custom], ignore_index=True).drop_duplicates(subset=["Equipment"], keep="first")

# Ensure editor columns exist with proper types/defaults
editor_cols = ["Equipment","Mode","ROJ","PO Execution","Submittal (days)","Manufacturing (days)","Shipping (days)","Buffer (days)"]
for c in editor_cols:
    if c not in work_df.columns:
        if c == "Equipment": continue
        elif c == "Mode": work_df[c] = ""  # blank by default
        elif c in ("ROJ","PO Execution"): work_df[c] = pd.NaT
        elif c == "Manufacturing (days)": work_df[c] = 0
        elif c == "Submittal (days)": work_df[c] = DEFAULT_SUBMITTAL_DAYS
        elif c == "Shipping (days)": work_df[c] = DEFAULT_SHIPPING_DAYS
        elif c == "Buffer (days)": work_df[c] = DEFAULT_BUFFER_DAYS

# Coerce types BEFORE editor so DateColumn works and numbers are numeric
work_df["ROJ"] = pd.to_datetime(work_df["ROJ"], errors="coerce")
work_df["PO Execution"] = pd.to_datetime(work_df["PO Execution"], errors="coerce")
for num_col in ["Submittal (days)","Manufacturing (days)","Shipping (days)","Buffer (days)"]:
    work_df[num_col] = pd.to_numeric(work_df[num_col], errors="coerce").fillna(0).astype(int)

# Persist to session
st.session_state.work_df = work_df[editor_cols].copy()

st.markdown("### Equipment & Durations")
edited_df = st.data_editor(
    st.session_state.work_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Mode": st.column_config.SelectboxColumn("Mode", options=["","Forward","Backward"]),
        "ROJ": st.column_config.DateColumn("ROJ"),
        "PO Execution": st.column_config.DateColumn("PO Execution"),
        "Submittal (days)": st.column_config.NumberColumn(min_value=0, step=1),
        "Manufacturing (days)": st.column_config.NumberColumn(min_value=0, step=1),
        "Shipping (days)": st.column_config.NumberColumn(min_value=0, step=1),
        "Buffer (days)": st.column_config.NumberColumn(min_value=0, step=1),
    },
)
# Coerce types AGAIN after edit to keep consistency (prevents “disappearing” dates)
edited_df["ROJ"] = pd.to_datetime(edited_df["ROJ"], errors="coerce")
edited_df["PO Execution"] = pd.to_datetime(edited_df["PO Execution"], errors="coerce")
for num_col in ["Submittal (days)","Manufacturing (days)","Shipping (days)","Buffer (days)"]:
    edited_df[num_col] = pd.to_numeric(edited_df[num_col], errors="coerce").fillna(0).astype(int)
st.session_state.work_df = edited_df.copy()

# ============ Compute ============
def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        mode = (row.get("Mode") or "").strip()
        if mode not in ("Forward","Backward"):
            continue  # skip until user chooses a mode
        res = compute_pass(row, mode, holidays=holiday_set)
        if not res:
            continue

        # Validation
        status = ""
        flt = None
        delta = None
        if mode == "Backward":
            po_req = res.get("PO Execution")
            if pd.notna(po_req) and po_req < TODAY:
                status = "⚠️ Past‑due PO"
                s = bday_diff(po_req, TODAY, holiday_set)
                flt = -abs(s) if s is not None else None
        else:  # Forward
            roj_calc = res.get("ROJ")
            roj_target = pd.to_datetime(row.get("ROJ"))
            if pd.notna(roj_calc) and pd.notna(roj_target) and roj_calc > roj_target:
                status = "⛔ Not achievable"
                delta = bday_diff(roj_target, roj_calc, holiday_set)

        rec = {"Equipment": row.get("Equipment",""), "Mode": mode}
        rec.update(res)
        rec.update({
            "Submittal (days)": row.get("Submittal (days)", DEFAULT_SUBMITTAL_DAYS),
            "Manufacturing (days)": row.get("Manufacturing (days)", 0),
            "Shipping (days)": row.get("Shipping (days)", DEFAULT_SHIPPING_DAYS),
            "Buffer (days)": row.get("Buffer (days)", DEFAULT_BUFFER_DAYS),
            "Status": status,
            "Float (days)": flt,
            "Delta to Target ROJ (days)": delta,
        })
        records.append(rec)
    return pd.DataFrame(records)

results_df = compute_all(st.session_state.work_df)

# ============ Output: Table ============
st.markdown("### Calculated Dates")
if results_df.empty:
    st.info("Choose Mode per row and enter either ROJ (Backward) or PO Execution (Forward).")
else:
    show_df = results_df.copy()
    for c in show_df.columns:
        if "Start" in c or "End" in c or c in {"PO Execution","ROJ"}:
            show_df[c] = pd.to_datetime(show_df[c]).dt.date
    st.dataframe(show_df, use_container_width=True, hide_index=True)
    csv = show_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Results (CSV)", data=csv, file_name="procurement_pass_results.csv", mime="text/csv")

# ============ Output: Gantt ============
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
            s = r.get(s_col); e = r.get(e_col)
            if pd.isna(s) or pd.isna(e): 
                continue
            bars.append({
                "Equipment": r["Equipment"], "Phase": phase,
                "Start": pd.to_datetime(s), "Finish": pd.to_datetime(e)
            })
    if bars:
        gantt_df = pd.DataFrame(bars)
        color_map = {
            "Submittal": MANO_BLUE,      # #1b6a87
            "Manufacturing": "#DECADE",
            "Shipping": "#F6AE2D",
            "Buffer": "#F34213",
        }
        fig = px.timeline(
            gantt_df,
            x_start="Start", x_end="Finish",
            y="Equipment",
            color="Phase",
            category_orders={"Phase": ["Submittal","Manufacturing","Shipping","Buffer"]},
            color_discrete_map=color_map,
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=520, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline bars yet — enter dates to calculate first.")


