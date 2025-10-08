# ---- v7.5 ----

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime

import utils.css as styling
import utils.calendar as calendar
import utils.colors as colors

# ---- Plotly guard ----
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ModuleNotFoundError:
    st.error("Plotly isn’t installed. Run: pip install streamlit pandas numpy plotly")
    st.stop()

st.set_page_config(page_title="Procurement Calculator", layout="wide")
styling.inject_custom_css()
st.logo("./assets/images/Mano_Logo_Main.svg", icon_image="./assets/images/Mano_Mark_Mark.svg")

# ================= Defaults / Constants =================
DEFAULT_SUBMITTAL_DAYS = 15
DEFAULT_SHIPPING_DAYS  = 15
DEFAULT_BUFFER_DAYS    = 20
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

# ================= Helpers =================
def as_int(x, default=0):
    try:
        if pd.isna(x) or x == "":
            return default
        return int(float(x))
    except Exception:
        return default

def bday_add(start, days, holidays=None):
    if pd.isna(start) or days is None: return pd.NaT
    return pd.to_datetime(np.busday_offset(np.datetime64(pd.to_datetime(start).date()),
                                           int(days), holidays=sorted(list(holidays or set())), roll="forward"))

def bday_sub(end, days, holidays=None):
    if pd.isna(end) or days is None: return pd.NaT
    return pd.to_datetime(np.busday_offset(np.datetime64(pd.to_datetime(end).date()),
                                           -int(days), holidays=sorted(list(holidays or set())), roll="backward"))

def bday_diff(d1, d2, holidays):
    if pd.isna(d1) or pd.isna(d2): return None
    return int(np.busday_count(np.datetime64(pd.to_datetime(d1).date()),
                               np.datetime64(pd.to_datetime(d2).date()),
                               holidays=sorted(list(holidays or set()))))

def compute_pass(row, mode, holidays):
    sub  = as_int(row.get("Submittal (days)"), DEFAULT_SUBMITTAL_DAYS)
    mfg  = as_int(row.get("Manufacturing (days)"), 0)
    ship = as_int(row.get("Shipping (days)"),  DEFAULT_SHIPPING_DAYS)
    buf  = as_int(row.get("Buffer (days)"),    DEFAULT_BUFFER_DAYS)
    po   = pd.to_datetime(row.get("PO Execution"), errors="coerce")
    roj  = pd.to_datetime(row.get("ROJ"), errors="coerce")

    if mode == "Forward":
        if pd.isna(po): return {}
        sub_end = bday_add(po, sub, holidays)
        mfg_end = bday_add(sub_end, mfg, holidays)
        ship_end = bday_add(mfg_end, ship, holidays)
        roj_calc = bday_add(ship_end, buf, holidays)
        return {"PO Execution": po,
                "Submittal Start": po, "Submittal End": sub_end,
                "Manufacturing Start": sub_end, "Manufacturing End": mfg_end,
                "Shipping Start": mfg_end, "Shipping End": ship_end,
                "Buffer Start": ship_end, "ROJ_calc": roj_calc, "Buffer End": roj_calc}

    if mode == "Backward":
        if pd.isna(roj): return {}
        ship_end = bday_sub(roj, buf, holidays)
        mfg_end  = bday_sub(ship_end, ship, holidays)
        sub_end  = bday_sub(mfg_end, mfg, holidays)
        po_calc  = bday_sub(sub_end, sub, holidays)
        if pd.notna(po_calc) and po_calc < TODAY:
            po_calc = TODAY
        return {"PO Execution": po_calc,
                "Submittal Start": po_calc, "Submittal End": sub_end,
                "Manufacturing Start": sub_end, "Manufacturing End": mfg_end,
                "Shipping Start": mfg_end, "Shipping End": ship_end,
                "Buffer Start": ship_end, "ROJ_calc": roj, "Buffer End": roj}
    return {}

def compute_all(df: pd.DataFrame, holiday_set) -> pd.DataFrame:
    recs = []
    if df is None or df.empty:
        return pd.DataFrame()

    calc = df.copy()
    for c in ["ROJ","PO Execution","Delivery Date (committed)"]:
        calc[c] = pd.to_datetime(calc.get(c), errors="coerce")
    for c in ["Submittal (days)","Manufacturing (days)","Shipping (days)","Buffer (days)"]:
        calc[c] = pd.to_numeric(calc.get(c), errors="coerce")

    for _, row in calc.iterrows():
        mode = str(row.get("Mode","") or "")
        if mode not in ("Forward","Backward"):
            continue

        committed_delivery = row.get("Delivery Date (committed)")
        po = row.get("PO Execution")
        sub = as_int(row.get("Submittal (days)"), DEFAULT_SUBMITTAL_DAYS)
        mfg = row.get("Manufacturing (days)")
        ship = as_int(row.get("Shipping (days)"), DEFAULT_SHIPPING_DAYS)
        buf = as_int(row.get("Buffer (days)"), DEFAULT_BUFFER_DAYS)

        # Derive Manufacturing (days) if committed delivery is present (Forward)
        def _needs_mfg_calc(val):
            if pd.isna(val):
                return True
            if isinstance(val, str) and val.strip() == "":
                return True
            try:
                return float(val) == 0.0
            except Exception:
                return False

        if mode == "Forward" and pd.notna(committed_delivery) and _needs_mfg_calc(mfg) and pd.notna(po):
            mfg_end = bday_sub(committed_delivery, buf, holiday_set)
            mfg_end = bday_sub(mfg_end, ship, holiday_set)
            sub_end = bday_add(po, sub, holiday_set)
            if pd.notna(sub_end) and pd.notna(mfg_end):
                mfg_dur = bday_diff(sub_end, mfg_end, holiday_set)
                if mfg_dur is not None and mfg_dur < 0:
                    mfg_dur = 0
                row["Manufacturing (days)"] = mfg_dur

        res = compute_pass(row, mode, holiday_set)
        if not res:
            status_msg = "Missing inputs for calculation."
            po_display = row.get("PO Execution")
            if mode == "Forward" and pd.isna(po):
                status_msg = "⚠️Missing PO Execution; dates not computed"
                po_display = None

            recs.append({
                "Equipment": row.get("Equipment",""),
                "Mode": mode,
                "ROJ": row.get("ROJ"),
                "PO Execution": po_display,
                "Submittal (days)": sub,
                "Submittal Start": None,
                "Submittal End": None,
                "Manufacturing (days)": as_int(row.get("Manufacturing (days)"), 0),
                "Manufacturing Start": None,
                "Manufacturing End": None,
                "Shipping (days)": ship,
                "Shipping Start": None,
                "Shipping End": None,
                "Buffer (days)": buf,
                "Buffer Start": None,
                "Status": status_msg,
                "Delta/Float (days)": None,
                "Delivery Date (committed)": committed_delivery,
                "Delivery Date": None,
            })
            continue

        ship_end = res.get("Shipping End")
        buffer_end = res.get("Buffer End")
        computed_delivery = buffer_end if buf > 0 else ship_end
        final_delivery = computed_delivery

        roj_user = row.get("ROJ")

        delta = None
        status = ""
        if pd.notna(roj_user) and pd.notna(final_delivery):
            delta = bday_diff(roj_user, final_delivery, holiday_set)
            if delta is not None and delta > 0:
                status = "⛔Late vs ROJ"
            elif delta is not None and delta <= 0:
                status = "✓ Meets/early vs ROJ"

        flt = None
        if mode == "Backward":
            po_req = res.get("PO Execution")
            if pd.notna(po_req):
                flt = bday_diff(TODAY, po_req, holiday_set)
                if flt is not None and flt <= 22:
                    status = "‼️PO is critical. Execute ASAP"

        combo = delta if delta is not None else flt

        d = {
            "Equipment": row.get("Equipment",""),
            "Mode": mode,
            "ROJ": roj_user,
            "PO Execution": res.get("PO Execution"),
            "Submittal (days)": sub,
            "Submittal Start": res.get("Submittal Start"), "Submittal End": res.get("Submittal End"),
            "Manufacturing (days)": as_int(row.get("Manufacturing (days)"), 0),
            "Manufacturing Start": res.get("Manufacturing Start"), "Manufacturing End": res.get("Manufacturing End"),
            "Shipping (days)": ship,
            "Shipping Start": res.get("Shipping Start"), "Shipping End": res.get("Shipping End"),
            "Buffer (days)": buf, "Buffer Start": res.get("Buffer Start"),
            "Status": status if status else None,
            "Delta/Float (days)": combo,
            "Delivery Date (committed)": committed_delivery,
            "Delivery Date": final_delivery,
        }
        recs.append(d)

    if not recs:
        return pd.DataFrame()

    out = pd.DataFrame(recs)
    table_cols = [
        "Equipment","Mode","ROJ","PO Execution",
        "Submittal (days)","Submittal Start","Submittal End",
        "Manufacturing (days)","Manufacturing Start","Manufacturing End",
        "Shipping (days)","Shipping Start","Shipping End",
        "Buffer (days)","Buffer Start",
        "Status","Delta/Float (days)",
        "Delivery Date (committed)","Delivery Date",
    ]
    existing = [c for c in table_cols if c in out.columns]
    return out[existing]

# ====== NEW: Baseline helpers ===================================================
DATE_COLS = [
    "PO Execution","Submittal Start","Submittal End",
    "Manufacturing Start","Manufacturing End",
    "Shipping Start","Shipping End",
    "Buffer Start","Delivery Date","ROJ","Delivery Date (committed)"
]

def _norm_dates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    for c in DATE_COLS:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce")
    return out

def compare_to_baseline(current: pd.DataFrame, baseline: pd.DataFrame, holiday_set) -> pd.DataFrame:
    """Return a tidy comparison with Δ (business days) per key date."""
    if current is None or current.empty or baseline is None or baseline.empty:
        return pd.DataFrame()

    cur = _norm_dates(current)
    base = _norm_dates(baseline)

    # Merge on Equipment (assumes unique Equipment per row; if not, consider adding an ID)
    merged = pd.merge(
        base.add_prefix("Base: "),
        cur.add_prefix("New: "),
        left_on="Base: Equipment", right_on="New: Equipment",
        how="outer", indicator=True
    )

    # Compute deltas for each comparable date field
    def delta_col(col_name):
        bcol = f"Base: {col_name}"
        ncol = f"New: {col_name}"
        if bcol in merged.columns and ncol in merged.columns:
            merged[f"Δ {col_name} (bd)"] = merged.apply(
                lambda r: bday_diff(r[bcol], r[ncol], holiday_set) if not (pd.isna(r[bcol]) or pd.isna(r[ncol])) else None,
                axis=1
            )

    for c in ["PO Execution","Submittal End","Manufacturing End","Shipping End","Delivery Date","ROJ"]:
        delta_col(c)

    # Flags
    merged["Changed?"] = merged.apply(
        lambda r: any([
            r.get(f"Δ {c} (bd)") not in (None, 0) for c in ["PO Execution","Submittal End","Manufacturing End","Shipping End","Delivery Date","ROJ"]
        ]),
        axis=1
    )

    # Pretty ordering
    keep = [
        "New: Equipment","Changed?",
        "Base: Mode","New: Mode",
        "Base: PO Execution","New: PO Execution","Δ PO Execution (bd)",
        "Base: Submittal End","New: Submittal End","Δ Submittal End (bd)",
        "Base: Manufacturing End","New: Manufacturing End","Δ Manufacturing End (bd)",
        "Base: Shipping End","New: Shipping End","Δ Shipping End (bd)",
        "Base: Delivery Date","New: Delivery Date","Δ Delivery Date (bd)",
        "Base: ROJ","New: ROJ","Δ ROJ (bd)",
        "Base: Status","New: Status","Base: Delta/Float (days)","New: Delta/Float (days)"
    ]
    keep = [c for c in keep if c in merged.columns]
    merged = merged[keep].rename(columns={"New: Equipment":"Equipment"})
    return merged

# ================= Title & Notes =================
st.title("Procurement Calculator")
with st.expander("Assumptions & Notes", expanded=True):
    st.markdown(
        """
<div class="small-muted mb-2">
<b>Assumptions:</b> Business-day math (Mon–Fri). Choose a single holiday preset.<br>
<b>Per-row Mode:</b> Forward = compute from PO; Backward = compute PO from ROJ.<br>
<b>Committed Delivery:</b> If present, leave <i>Manufacturing (days)</i> blank and we’ll derive it.<br>
<b>Backward PO cap:</b> If calculated PO lands before today, we cap it at today (manual past POs are allowed in Forward).<br>
</div>
""".strip(),
        unsafe_allow_html=True,
    )

# ================= Sidebar: Holiday presets =================
with st.sidebar:
    st.header("Holiday Calendar")
    calendar_choice = st.selectbox("Preset", ["None","US Federal","Spain (C. Valenciana)","Netherlands","Italy","UK (England & Wales)","Mexico"])
    holiday_set = calendar.build_for_region(calendar_choice)

# ================= Session init =================
def make_default_df():
    df = pd.DataFrame(STANDARD_EQUIPMENT)
    df["Mode"] = ""
    df["ROJ"] = pd.NaT
    df["PO Execution"] = pd.NaT
    df["Submittal (days)"] = DEFAULT_SUBMITTAL_DAYS
    df["Manufacturing (days)"] = 0
    df["Shipping (days)"]  = DEFAULT_SHIPPING_DAYS
    df["Buffer (days)"]    = DEFAULT_BUFFER_DAYS
    df["Delivery Date (committed)"] = pd.NaT
    return df

if "work_df" not in st.session_state or st.session_state.work_df is None:
    st.session_state.work_df = make_default_df()
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()
if "editor_nonce" not in st.session_state:
    st.session_state.editor_nonce = 0

# ====== NEW: baseline session slots ============================================
if "baseline" not in st.session_state:
    st.session_state.baseline = pd.DataFrame()
if "baseline_meta" not in st.session_state:
    st.session_state.baseline_meta = {}
if "baseline_notice" not in st.session_state:
    st.session_state.baseline_notice = None

# ================= Top buttons (Clear / Baseline) =================
# c2, c3, _ = st.columns([1,1,5], gap="small")
# with c1:
#     if st.button("Clear All Inputs"):
#         df = st.session_state.work_df.copy()
#         for c in ["Mode","ROJ","PO Execution","Delivery Date (committed)"]:
#             if c == "Mode" and c in df:
#                 df[c] = ""
#             elif c in df:
#                 df[c] = pd.NaT
#         for c in ["Submittal (days)","Manufacturing (days)","Shipping (days)","Buffer (days)"]:
#             if c in df:
#                 if c == "Manufacturing (days)":
#                     df[c] = 0
#                 elif c == "Submittal (days)":
#                     df[c] = DEFAULT_SUBMITTAL_DAYS
#                 elif c == "Shipping (days)":
#                     df[c] = DEFAULT_SHIPPING_DAYS
#                 elif c == "Buffer (days)":
#                     df[c] = DEFAULT_BUFFER_DAYS
#         st.session_state.work_df = df
#         st.session_state.results = pd.DataFrame()
#         st.session_state.editor_nonce += 1

# ====== NEW: Baseline lock / reset =============================================
# with c2:
#     # Enable if there are results OR at least one row has a Mode set
#     has_modes = False
#     if isinstance(st.session_state.work_df, pd.DataFrame) and "Mode" in st.session_state.work_df.columns:
#         modes_series = st.session_state.work_df["Mode"].fillna("")
#         has_modes = modes_series.isin(["Forward", "Backward"]).any()

#     has_results = st.session_state.results is not None and not st.session_state.results.empty
#     lockable = has_results or has_modes

#     if st.button("Lock Baseline", disabled=not lockable):
#         # Ensure we lock the latest calc; if empty, compute on the fly
#         current = st.session_state.results
#         if current is None or current.empty:
#             current = compute_all(st.session_state.work_df, holiday_set)

#         base = current.copy()
#         for c in [
#             "PO Execution","Submittal Start","Submittal End",
#             "Manufacturing Start","Manufacturing End",
#             "Shipping Start","Shipping End",
#             "Buffer Start","Delivery Date","ROJ","Delivery Date (committed)"
#         ]:
#             if c in base.columns:
#                 base[c] = pd.to_datetime(base[c], errors="coerce")

#         st.session_state.baseline = base
#         st.session_state.baseline_meta = {
#             "locked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
#             "calendar": calendar_choice,
#         }

# with c3:
#     if st.button("Reset Baseline", disabled=st.session_state.baseline.empty):
#         st.session_state.baseline = pd.DataFrame()
#         st.session_state.baseline_meta = {}

# ================= Data Editor (FORM; Calculate-only) =================

st.markdown("### Equipment & Durations")
st.caption("Only fill **Delivery Date (committed)** if a vendor has provided a firm date. If so, leave **Manufacturing (days)** blank and we’ll derive it.")

editor_cols = [
    "Equipment","Mode","ROJ","PO Execution",
    "Submittal (days)","Manufacturing (days)","Shipping (days)","Buffer (days)",
    "Delivery Date (committed)"
]
for c in editor_cols:
    if c not in st.session_state.work_df.columns:
        if c in ("Equipment","Mode"):
            st.session_state.work_df[c] = ""
        elif c in ("ROJ","PO Execution","Delivery Date (committed)"):
            st.session_state.work_df[c] = pd.NaT
        elif c == "Manufacturing (days)":
            st.session_state.work_df[c] = 0
        elif c == "Submittal (days)":
            st.session_state.work_df[c] = DEFAULT_SUBMITTAL_DAYS
        elif c == "Shipping (days)":
            st.session_state.work_df[c] = DEFAULT_SHIPPING_DAYS
        elif c == "Buffer (days)":
            st.session_state.work_df[c] = DEFAULT_BUFFER_DAYS

with st.form("grid_form", clear_on_submit=False):
    edited_df = st.data_editor(
        st.session_state.work_df[editor_cols],
        key=f"equipment_editor_{st.session_state.editor_nonce}",
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=editor_cols,
        column_config={
            "Mode": st.column_config.SelectboxColumn("Mode", options=["","Forward","Backward"]),
            "ROJ": st.column_config.DateColumn("ROJ"),
            "PO Execution": st.column_config.DateColumn("PO Execution"),
            "Submittal (days)":     st.column_config.NumberColumn(min_value=0, step=1),
            "Manufacturing (days)": st.column_config.NumberColumn(min_value=0, step=1),
            "Shipping (days)":      st.column_config.NumberColumn(min_value=0, step=1),
            "Buffer (days)":        st.column_config.NumberColumn(min_value=0, step=1),
            "Delivery Date (committed)": st.column_config.DateColumn("Delivery Date (committed)"),
        },
    )
    # calc_clicked = st.form_submit_button("Calculate", type="primary")
    col1, col2 = st.columns([1, 1])
    with col2:
        calc_clicked = st.form_submit_button("Calculate", type="primary")
    with col1:
        reset = st.form_submit_button("Clear All Inputs", type="secondary")

if calc_clicked:
    st.session_state.work_df = edited_df.copy()
    st.session_state.results = compute_all(st.session_state.work_df, holiday_set)

if reset:
    df = st.session_state.work_df.copy()
    for c in ["Mode","ROJ","PO Execution","Delivery Date (committed)"]:
        if c == "Mode" and c in df:
            df[c] = ""
        elif c in df:
            df[c] = pd.NaT
    for c in ["Submittal (days)","Manufacturing (days)","Shipping (days)","Buffer (days)"]:
        if c in df:
            if c == "Manufacturing (days)":
                df[c] = 0
            elif c == "Submittal (days)":
                df[c] = DEFAULT_SUBMITTAL_DAYS
            elif c == "Shipping (days)":
                df[c] = DEFAULT_SHIPPING_DAYS
            elif c == "Buffer (days)":
                df[c] = DEFAULT_BUFFER_DAYS
    st.session_state.work_df = df
    st.session_state.results = pd.DataFrame()   # clear output
    st.session_state.editor_nonce += 1          # force editor refresh


# ================= Output: Table =================
st.markdown("### Calculated Dates")

def renderBaselineButtons(c2, c3, c4):
  # ====== NEW: Baseline lock / reset =============================================
  with c2:
      # Enable if there are results OR at least one row has a Mode set
      has_modes = False
      if isinstance(st.session_state.work_df, pd.DataFrame) and "Mode" in st.session_state.work_df.columns:
          modes_series = st.session_state.work_df["Mode"].fillna("")
          has_modes = modes_series.isin(["Forward", "Backward"]).any()

      has_results = st.session_state.results is not None and not st.session_state.results.empty
      lockable = has_results or has_modes

      if st.button("Lock Baseline", disabled=not lockable, type="primary"):
          # Ensure we lock the latest calc; if empty, compute on the fly
          current = st.session_state.results
          if current is None or current.empty:
              current = compute_all(st.session_state.work_df, holiday_set)

          base = current.copy()
          for c in [
              "PO Execution","Submittal Start","Submittal End",
              "Manufacturing Start","Manufacturing End",
              "Shipping Start","Shipping End",
              "Buffer Start","Delivery Date","ROJ","Delivery Date (committed)"
          ]:
              if c in base.columns:
                  base[c] = pd.to_datetime(base[c], errors="coerce")

          st.session_state.baseline = base
          st.session_state.baseline_meta = {
              "locked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
              "calendar": calendar_choice,
          }

  with c3:
      can_adopt = (st.session_state.results is not None and not st.session_state.results.empty and
                   not st.session_state.baseline.empty)
      if st.button("Adopt Scenario", disabled=not can_adopt, type="primary"):
          st.session_state.baseline = pd.DataFrame()
          st.session_state.baseline_meta = {}
          st.session_state.baseline_notice = "New scenario adopted. Baseline cleared."

  with c4:
      if st.button("Reset Baseline", disabled=st.session_state.baseline.empty, type="secondary"):
          st.session_state.baseline = pd.DataFrame()
          st.session_state.baseline_meta = {}
          st.session_state.baseline_notice = "Baseline cleared."

if st.session_state.results is None or st.session_state.results.empty:
    st.info("Fill the table, then click **Calculate**.")
else:
    # View toggle: Current vs Compare
    view = "Current"
    if not st.session_state.baseline.empty:
        meta = st.session_state.baseline_meta
        blurb = f" (baseline {meta.get('locked_at','')} – {meta.get('calendar','')})"
        view = st.radio("View", ["Current","Compare to Baseline"], horizontal=True, index=0, help="Lock a baseline, then compare.")
        st.caption(f"Baseline locked{blurb}")

    notice = st.session_state.get("baseline_notice")
    if notice:
        st.success(notice)
        st.session_state.baseline_notice = None

    # Format helper
    def _dates_to_date(df):
        out = df.copy()
        for c in out.columns:
            if ("Start" in c or "End" in c or c in {"PO Execution","ROJ","Delivery Date (committed)","Delivery Date"}) and pd.api.types.is_datetime64_any_dtype(out[c]):
                out[c] = pd.to_datetime(out[c]).dt.date
        return out

    if view == "Current":
        show = _dates_to_date(st.session_state.results.copy())
        st.dataframe(show, use_container_width=True, hide_index=True)
        # ================= Buttons Baseline =================
        c2, c3, c4, _, c1 = st.columns([2,2,2,4,3], gap="small")
        with c1: st.download_button("Download Results (CSV)", data=show.to_csv(index=False).encode("utf-8"),
                           file_name="procurement_pass_results.csv", mime="text/csv")
        renderBaselineButtons(c2, c3, c4)
    else:
        comp = compare_to_baseline(st.session_state.results, st.session_state.baseline, holiday_set)
        # Show deltas with simple emoji cues
        def delta_icon(v):
            if pd.isna(v) or v == 0: return ""
            return "▲" if v and v > 0 else "▼"
        display = comp.copy()
        for c in [col for col in display.columns if col.startswith("Δ ")]:
            display[c] = display[c].apply(lambda v: f"{delta_icon(v)} {v} bd" if pd.notna(v) else "")
        # Dates to date
        date_like_cols = {
            "Base: PO Execution","Base: Submittal End","Base: Manufacturing End",
            "Base: Shipping End","Base: Delivery Date","Base: ROJ",
            "Base: Delivery Date (committed)",
            "New: PO Execution","New: Submittal End","New: Manufacturing End",
            "New: Shipping End","New: Delivery Date","New: ROJ",
            "New: Delivery Date (committed)",
        }
        for c in display.columns:
            if c in date_like_cols:
                display[c] = pd.to_datetime(display[c], errors="coerce").dt.date
        st.dataframe(display, use_container_width=True, hide_index=True)
        # ================= Buttons Baseline =================
        c2, c3, c4, _, c1 = st.columns([2,2,2,4,3], gap="small")
        with c1:
          st.download_button("Download Compare (CSV)", data=comp.to_csv(index=False).encode("utf-8"),
                           file_name="procurement_baseline_compare.csv", mime="text/csv")
        renderBaselineButtons(c2, c3, c4)

# ================= Output: Gantt =================
st.markdown("### Timeline (per Equipment)")
res = st.session_state.results
if res is not None and not res.empty:
    bars = []
    phases = [("Submittal","Submittal Start","Submittal End"),
              ("Manufacturing","Manufacturing Start","Manufacturing End"),
              ("Shipping","Shipping Start","Shipping End"),
              ("Buffer","Buffer Start","Delivery Date")]

    # Current bars
    for _, r in res.iterrows():
        has_any = False
        for p, s, e in phases:
            s_val, e_val = r.get(s), r.get(e)
            if pd.isna(s_val) or pd.isna(e_val):
                continue
            has_any = True
            bars.append({"Series":"Current","Equipment": r["Equipment"], "Phase": p,
                         "Start": pd.to_datetime(s_val), "Finish": pd.to_datetime(e_val)})
        if pd.notna(r.get("ROJ")):
            roj_val = pd.to_datetime(r.get("ROJ"))
            bars.append({"Series":"Current","Equipment": r["Equipment"], "Phase": "ROJ",
                         "Start": roj_val, "Finish": roj_val + pd.Timedelta(days=1)})
        if not has_any and pd.isna(r.get("ROJ")):
            milestone = r.get("Delivery Date") or r.get("PO Execution")
            if pd.notna(milestone):
                start = pd.to_datetime(milestone)
                finish = start + pd.Timedelta(days=1)
                bars.append({"Series":"Current","Equipment": r["Equipment"], "Phase": "Milestone",
                             "Start": start, "Finish": finish})

    # ====== NEW: Baseline ghost bars ===========================================
    if not st.session_state.baseline.empty:
        base = st.session_state.baseline
        for _, r in base.iterrows():
            for p, s, e in phases:
                s_val, e_val = r.get(s), r.get(e)
                if pd.isna(s_val) or pd.isna(e_val):
                    continue
                bars.append({"Series":"Baseline","Equipment": r["Equipment"], "Phase": p,
                             "Start": pd.to_datetime(s_val), "Finish": pd.to_datetime(e_val)})
            if pd.notna(r.get("ROJ")):
                roj_val = pd.to_datetime(r.get("ROJ"))
                bars.append({"Series":"Baseline","Equipment": r["Equipment"], "Phase": "ROJ",
                             "Start": roj_val, "Finish": roj_val + pd.Timedelta(days=1)})

    if bars:
        gantt_df = pd.DataFrame(bars)

        # Color map: Current vivid, Baseline ghosted (same hues lower alpha)
        phase_colors = {
            "Submittal": colors.MANO_BLUE,
            "Manufacturing": colors.MANUFACTURING,
            "Shipping": colors.SHIPPING,
            "Buffer": colors.BUFFER,
            "ROJ": colors.MANO_GREY,
            "Milestone": colors.MANO_BLUE,
        }

        # Add combined Y axis label = Equipment + Series
        gantt_df["Equip"] = gantt_df["Equipment"] + " - " + gantt_df["Series"]

        # Order so Current is always above Baseline
        ordered_y = []
        for eq in gantt_df["Equipment"].unique():
          ordered_y.append(f"{eq} - Current")
          if f"{eq} - Baseline" in gantt_df["Equip"].values:
              ordered_y.append(f"{eq} - Baseline")
        
        # --- Current ---
        cur_df = gantt_df[gantt_df["Series"] == "Current"]
        fig = px.timeline(
            cur_df,
            x_start="Start",
            x_end="Finish",
            y="Equip",
            color="Phase",
            category_orders={
              "Phase": ["Submittal","Manufacturing","Shipping","Buffer","ROJ","Milestone"],
              "Equip": ordered_y,
            },
            color_discrete_map=phase_colors,
        )

        # --- Baseline ---
        base_df = gantt_df[gantt_df["Series"] == "Baseline"]
        if not base_df.empty:
          base_fig = px.timeline(
            base_df,
            x_start="Start",
            x_end="Finish",
            y="Equip",
            color="Phase",
            category_orders={
              "Phase": ["Submittal","Manufacturing","Shipping","Buffer","ROJ","Milestone"],
              "Equip": ordered_y,
            },
            color_discrete_map=phase_colors,
          )
          for tr in base_fig.data:
            tr.opacity = 0.25       # 👈 ghosted baseline
            tr.showlegend = False   # avoid duplicate legend
            tr.width = 0.5
            fig.add_trace(tr)

        tick_map = {}
        for eq in gantt_df["Equipment"].unique():
          tick_map[f"{eq} - Current"] = eq        # show just equipment name
          tick_map[f"{eq} - Baseline"] = ""  # indented baseline

        # Axes + layout
        fig.update_xaxes(
          showgrid=True,
          gridcolor="lightgray",
          linewidth=1,
          linecolor=colors.MANO_BLUE,
          title="Timeline"
        )
        fig.update_yaxes(
          showgrid=True,
          autorange="reversed",
          tickmode="array",
          tickvals=list(tick_map.keys()),   # real values
          ticktext=list(tick_map.values()), # what gets shown,
          categoryorder="array",
          categoryarray=ordered_y,
          linewidth=1,
          linecolor=colors.MANO_BLUE,
          title="Equipment"
        )

        fig.update_layout(
            height=520,
            margin=dict(l=20, r=20, t=20, b=20),
            legend_title_text="",
            plot_bgcolor="#FFFFFF",
            paper_bgcolor=colors.MANO_OFFWHITE
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline bars yet — click **Calculate** first.")

