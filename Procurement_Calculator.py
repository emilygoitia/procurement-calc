# ---- v7.4 ----

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

import utils.css as styling
import utils.calendar as calendar
import utils.colors as colors

# ---- Plotly guard ----
try:
    import plotly.express as px
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
    """Forward/backward engine using business-day math."""
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
        # Cap calculated required PO at today (don’t say it was needed earlier than today)
        if pd.notna(po_calc) and po_calc < TODAY:
            po_calc = TODAY
        return {"PO Execution": po_calc,
                "Submittal Start": po_calc, "Submittal End": sub_end,
                "Manufacturing Start": sub_end, "Manufacturing End": mfg_end,
                "Shipping Start": mfg_end, "Shipping End": ship_end,
                "Buffer Start": ship_end, "ROJ_calc": roj, "Buffer End": roj}
    return {}

def compute_all(df: pd.DataFrame, holiday_set) -> pd.DataFrame:
    """Compute result rows from editor data. Requires holiday_set."""
    recs = []
    if df is None or df.empty:
        return pd.DataFrame()

    # Soft coercions
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

        # If committed delivery provided and mfg blank, derive Manufacturing (days) (Forward logic)
        if mode == "Forward" and pd.notna(committed_delivery) and (pd.isna(mfg) or mfg == "") and pd.notna(po):
            mfg_end = bday_sub(committed_delivery, buf, holiday_set)
            mfg_end = bday_sub(mfg_end, ship, holiday_set)
            sub_end = bday_add(po, sub, holiday_set)
            if pd.notna(sub_end) and pd.notna(mfg_end):
                mfg_dur = bday_diff(sub_end, mfg_end, holiday_set)
                if mfg_dur is not None and mfg_dur < 0:
                    mfg_dur = 0
                row["Manufacturing (days)"] = mfg_dur

        # Guard: Forward needs PO
        if mode == "Forward" and pd.isna(po):
            recs.append({
                "Equipment": row.get("Equipment",""),
                "Mode": mode,
                "ROJ": row.get("ROJ"),  # user ROJ only (no computed)
                "PO Execution": None,
                "Submittal (days)": sub, "Submittal Start": None, "Submittal End": None,
                "Manufacturing (days)": as_int(row.get("Manufacturing (days)"), 0),
                "Manufacturing Start": None, "Manufacturing End": None,
                "Shipping (days)": ship, "Shipping Start": None, "Shipping End": None,
                "Buffer (days)": buf, "Buffer Start": None,
                "Status": "ℹ️ PO missing; cannot calculate forward.",
                "Delta/Float (days)": None,
                "Delivery Date (committed)": committed_delivery,
                "Delivery Date": None,
            })
            continue

        res = compute_pass(row, mode, holiday_set)
        if not res:
            # e.g., Backward without ROJ
            recs.append({
                "Equipment": row.get("Equipment",""),
                "Mode": mode,
                "ROJ": row.get("ROJ"),
                "PO Execution": row.get("PO Execution"),
                "Submittal (days)": sub,
                "Manufacturing (days)": as_int(row.get("Manufacturing (days)"), 0),
                "Shipping (days)": ship,
                "Buffer (days)": buf,
                "Status": "ℹ️ Missing inputs for calculation.",
                "Delta/Float (days)": None,
                "Delivery Date (committed)": committed_delivery,
                "Delivery Date": None,
            })
            continue

        # Delivery Date (final): always compute from PO -> Submittal -> Manufacturing -> Shipping -> Buffer
        # (business-day math). Any user-committed date is retained separately but does not override
        # the calculated result so we can compare the two.
        ship_end = res.get("Shipping End")
        buffer_end = res.get("Buffer End")
        computed_delivery = buffer_end if buf > 0 else ship_end
        final_delivery = computed_delivery

        # ROJ column in results: only user-entered (no computed ROJ)
        roj_user = row.get("ROJ")

        # Delta to ROJ: compare user ROJ vs final delivery, if both present
        delta = None
        status = ""
        if pd.notna(roj_user) and pd.notna(final_delivery):
            delta = bday_diff(roj_user, final_delivery, holiday_set)
            if delta is not None and delta > 0:
                status = "⛔ Late vs ROJ"
            elif delta is not None and delta <= 0:
                status = "✓ Meets/early vs ROJ"

        # Float (Backward): business days from today to required PO date (capped in compute_pass)
        flt = None
        if mode == "Backward":
            po_req = res.get("PO Execution")
            if pd.notna(po_req):
                flt = bday_diff(TODAY, po_req, holiday_set)
                if flt is not None and flt <= 22:
                    status = "‼️ PO is critical. Execute ASAP"

        # Combined metric: delta if ROJ present, else float
        combo = delta if delta is not None else flt

        d = {
            "Equipment": row.get("Equipment",""),
            "Mode": mode,
            "ROJ": roj_user,                             # user-entered only
            "PO Execution": res.get("PO Execution"),     # computed or user
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
            "Delivery Date": final_delivery,             # final for results
        }
        recs.append(d)

    if not recs:
        return pd.DataFrame()

    out = pd.DataFrame(recs)
    # Results column order (ROJ kept, Delivery columns at the end)
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

# ================= Title & Notes =================
st.title("Procurement Calculator")
st.subheader("Assumptions & Notes")
st.markdown(
    """
<div class="small-muted">
<b>Assumptions:</b> Business-day math (Mon–Fri). Choose a single holiday preset.<br>
<b>Per-row Mode:</b> Forward = compute from PO; Backward = compute PO from ROJ.<br>
<b>Delivery Date (committed):</b> Only enter if a vendor has committed; if so, leave <i>Manufacturing (days)</i> blank and we’ll derive it.<br>
<b>PO Execution:</b> If calculated (Backward) and it lands before today, we cap it at today. Manually-entered past dates are allowed in Forward mode.<br>
</div>
""", unsafe_allow_html=True)

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
# Editor refresh nonce (force grid rebuild on clear/reset)
if "editor_nonce" not in st.session_state:
    st.session_state.editor_nonce = 0

# ================= Buttons =================
# c1, _ = st.columns([1,3], gap="small")
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
#         st.session_state.results = pd.DataFrame()   # clear output
#         st.session_state.editor_nonce += 1          # force editor refresh

# ================= Data Editor (FORM; Calculate-only) =================

st.markdown("### Equipment & Durations")
st.caption("Only fill **Delivery Date (committed)** if a vendor has provided a firm date. If so, leave **Manufacturing (days)** blank and we’ll derive it.")

editor_cols = [
    "Equipment","Mode","ROJ","PO Execution",
    "Submittal (days)","Manufacturing (days)","Shipping (days)","Buffer (days)",
    "Delivery Date (committed)"  # LAST
]
# Ensure columns exist with defaults
# for c in editor_cols:
#     if c not in st.session_state.work_df.columns:
#         if c in ("Equipment","Mode"):
#             st.session_state.work_df[c] = ""
#         elif c in ("ROJ","PO Execution","Delivery Date (committed)"):
#             st.session_state.work_df[c] = pd.NaT
#         elif c == "Manufacturing (days)":
#             st.session_state.work_df[c] = 0
#         elif c == "Submittal (days)":
#             st.session_state.work_df[c] = DEFAULT_SUBMITTAL_DAYS
#         elif c == "Shipping (days)":
#             st.session_state.work_df[c] = DEFAULT_SHIPPING_DAYS
#         elif c == "Buffer (days)":
#             st.session_state.work_df[c] = DEFAULT_BUFFER_DAYS

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
    col1, col2 = st.columns([1, 1])
    with col2:
        submit = st.form_submit_button("Calculate", type="primary")
    with col1:
        reset = st.form_submit_button("Reset", type="secondary")
    # calc_clicked = st.form_submit_button("Calculate", type="primary")

# On Calculate: persist edits and compute
if submit:
    st.session_state.work_df = edited_df.copy()
    st.session_state.results = compute_all(st.session_state.work_df, holiday_set)

#TODO: handle RESET w/ DEFAULTS
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
if st.session_state.results is None or st.session_state.results.empty:
    st.info("Fill the table, then click **Calculate**.")
else:
    show = st.session_state.results.copy()
    for c in show.columns:
        if "Start" in c or "End" in c or c in {"PO Execution","ROJ","Delivery Date (committed)","Delivery Date"}:
            show[c] = pd.to_datetime(show[c]).dt.date
    st.dataframe(show, use_container_width=True, hide_index=True)
    csv = show.to_csv(index=False).encode("utf-8")
    st.download_button("Download Results (CSV)", data=csv, file_name="procurement_pass_results.csv", mime="text/csv")

# ================= Output: Gantt =================
st.markdown("### Timeline (per Equipment)")
res = st.session_state.results
if res is not None and not res.empty:
    bars = []
    # Primary phase bars
    phases = [("Submittal","Submittal Start","Submittal End"),
              ("Manufacturing","Manufacturing Start","Manufacturing End"),
              ("Shipping","Shipping Start","Shipping End"),
              ("Buffer","Buffer Start","Delivery Date")]  # use final Delivery for Buffer end marker
    for _, r in res.iterrows():
        has_any = False
        for p, s, e in phases:
            s_val, e_val = r.get(s), r.get(e)
            if pd.isna(s_val) or pd.isna(e_val):
                continue
            has_any = True
            bars.append({"Equipment": r["Equipment"], "Phase": p,
                         "Start": pd.to_datetime(s_val), "Finish": pd.to_datetime(e_val)})
        # Always add ROJ milestone if provided. Give it a small width so it renders visibly.
        if pd.notna(r.get("ROJ")):
            roj_val = pd.to_datetime(r.get("ROJ"))
            bars.append({"Equipment": r["Equipment"], "Phase": "ROJ",
                         "Start": roj_val, "Finish": roj_val + pd.Timedelta(days=1)})
        # If no full phases and no ROJ, add a 1-day milestone so the equipment appears
        if not has_any and pd.isna(r.get("ROJ")):
            # Prefer Delivery, then PO
            milestone = r.get("Delivery Date") or r.get("PO Execution")
            if pd.notna(milestone):
                start = pd.to_datetime(milestone)
                finish = start + pd.Timedelta(days=1)
                bars.append({"Equipment": r["Equipment"], "Phase": "Milestone",
                             "Start": start, "Finish": finish})

    if bars:
        gantt_df = pd.DataFrame(bars)
        color_map = {
            "Submittal": colors.MANO_BLUE,
            "Manufacturing": colors.MANUFACTURING,
            "Shipping": colors.SHIPPING,
            "Buffer": colors.BUFFER,
            "ROJ": colors.MANO_GREY,
            "Milestone": colors.MANO_BLUE,
        }
        fig = px.timeline(
            gantt_df, x_start="Start", x_end="Finish", y="Equipment", color="Phase",
            category_orders={"Phase":["Submittal","Manufacturing","Shipping","Buffer","ROJ","Milestone"]},
            color_discrete_map=color_map,
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=520, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline bars yet — click **Calculate** first.")



