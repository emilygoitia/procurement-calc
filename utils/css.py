import streamlit as st
import utils.colors as colors

def inject_custom_css():
  BRAND_CSS = f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700&display=swap');
      :root {{
        --mano-blue: {colors.MANO_BLUE};
        --mano-offwhite: {colors.MANO_OFFWHITE};
        --mano-grey: {colors.MANO_GREY};
        --border-radius: 0.5rem;
      }}
      html, body, [class*="css"]  {{ font-family: 'Raleway', sans-serif; }}
      .stApp {{ background: var(--mano-offwhite); }}
      * {{ font-family: 'Raleway' !important; }}

      h1, h2, h3, h4, h5, h6 {{ 
        color: var(--mano-grey); 
        font-weight: 600;
      }}

      .my-2 {{
        margin-top: 2rem;
        margin-bottom: 2rem;
      }}
      .my-4 {{
        margin-top: 4rem;
        margin-bottom: 4rem;
      }}
      .mb-2 {{
        margin-bottom: 2rem;
      }}
      .mb-4 {{
        margin-bottom: 4rem;
      }}

      [data-testid="stDecoration"] {{
        display: none;
      }}
      [data-testid='stSidebarHeader'] {{
        position: sticky;
        top: 0;
        z-index: 1;
        background: #FFF;
      }}
      [data-testid="element-container"] {{
        max-width: 100% !important;
        width: 100% !important;
      }}
      [data-testid="stSlider"] {{
        max-width: 100% !important;
        width: 100% !important;
      }}
      [data-testid="stVerticalBlock"] {{
          max-width: 100% !important;
          width: 100% !important;
      }}
      [data-testid="stHorizontalBlock"] {{
          max-width: 100% !important;
          margin-bottom: 1rem;
      }}
      [data-testid="stMarkdownContainer"] {{
              display: flex;
              flex-direction: column;
      }}
      section[data-testid="stSidebar"] > div {{
        background: white;
        border-right: 2px solid var(--mano-blue); }}

      div[data-testid="stForm"] {{
        border: 0 !important;
        padding: 0 !important;
      }}

      .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {{
        font-size:1rem;
      }}

      .stDownloadButton {{
        display: flex;
        justify-content: flex-end;
      }}

      .stButton>button, .stDownloadButton>button {{
        background: var(--mano-blue);
        color: white;
        border: 1px solid transparent;
        border-radius: 12px;
        padding: .5rem 1rem;
        transition: background 0.3s, color 0.3s;
      }}
      .stButton > button:hover, .stDownloadButton > button:hover {{
        background: var(--mano-offwhite);
        color: var(--mano-blue);
        border-color: var(--mano-blue);
        border-radius: 12px;
        padding: .5rem 1rem;
      }}

      .stButton > button:focus:not(:active), .stDownloadButton > button:focus:not(:active) {{
        background: var(--mano-blue);
        color: var(--mano-offwhite);
      }}

      .dataframe tbody tr:nth-child(even) {{ background: #fff; }}

      .small-muted {{
        color: #5c6b73;
        font-size: 0.875rem;
        max-width: 1020px;
      }}

      .table-container {{
        max-height: 480px;
        overflow-y: auto;
        margin-bottom: 1rem;
        border-radius: var(--border-radius);
        border-bottom: 1px solid #bbb;
        box-sizing: content-box;
        scrollbar-width: thin;
        scrollbar-color: rgba(0,0,0,0.5) transparent;
      }}

      .table-container::-webkit-scrollbar {{
        width: 6px;
      }}
      .table-container::-webkit-scrollbar-track {{
        background: transparent;
      }}

      .styled-table {{
        font-family: 'Raleway', sans-serif;
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border: 0;
        margin-bottom: 0 !important;
      }}
      .styled-table thead th {{
        position: sticky;
        top: 0;
        z-index: 1;
      }}
      .styled-table td {{
        border: 0;
      }}
      .styled-table tr th, .styled-table tr td {{
        border-right: 1px solid #bbb;
        border-bottom: 1px solid #bbb;
      }}
      .styled-table tr:last-child td {{
        border-bottom: 0;
      }}
      .styled-table tr th:first-child, .styled-table tr td:first-child {{
        border-left: 1px solid #bbb;
      }}
      .styled-table tr th {{
        text-align: left;
        border-top: solid 1px #bbb;
      }}
      .styled-table tr {{ text-align: left !important; font-size: 0.875rem; }}
      .styled-table th {{ background: var(--mano-blue); color: var(--mano-offwhite); font-weight: 600; font-size: 0.875rem; box-shadow: 0 2px 5px rgba(0,0,0,0.25); }}
      .styled-table tr:first-child th:first-child {{border-top-left-radius: var(--border-radius);}}
      .styled-table tr:first-child th:last-child {{border-top-right-radius: var(--border-radius);}}
      .styled-table tr:last-child td:first-child {{border-bottom-left-radius: var(--border-radius);}}
      .styled-table tr:last-child td:last-child {{border-bottom-right-radius: var(--border-radius);}}

  
      div[data-testid='stVerticalBlockBorderWrapper']:has(>div>div>div>div>div[data-testid="stMarkdownContainer"]>.styled-slider){{
        padding: 10px;
        border-radius: 0.5rem;
      }}
      div[data-testid='stVerticalBlockBorderWrapper']:has(>div>div>div>div>div[data-testid="stMarkdownContainer"]>.styled-slider):nth-child(even){{ 
        background-color: var(--mano-offwhite);
      }}
      div[data-testid='stVerticalBlockBorderWrapper']:has(>div>div>div>div>div[data-testid="stMarkdownContainer"]>.styled-slider) [data-testid="stVerticalBlock"] {{
        gap: 0;
      }}

      .cards-wrapper {{
        container-type: inline-size;
        container-name: cards;
      }}
      .cards-container {{
        display: grid;
        grid-template-columns: repeat(1, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
      }}
      @container cards (width > 320px) {{
        .cards-container {{
          grid-template-columns: repeat(2, 1fr);
        }}
      }}
      @container cards (width > 720px) {{
        .cards-container {{
          grid-template-columns: repeat(4, 1fr);
        }}
      }}

      .kpi-card {{
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: white;
        padding: 12px;
        border-radius: 16px;
        border-left: 6px solid var(--mano-blue);
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
      }}
      .kpi-card p {{
        margin: 0;
        font-weight: 500;
        font-size: 0.675rem;
        color: var(--mano-grey);
      }}
      .kpi-card .label {{
        font-size: 1rem;
        font-weight: 600;
        color: var(--mano-grey);
      }}
      .kpi-card .date {{
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--mano-blue);
      }}

      .gridlayer .xgrid.crisp, .gridlayer .ygrid.crisp {{
        stroke-dasharray: 2;
      }}
      .yaxislayer-above {{
        transform: translateX(-0.5rem);
      }}
      .xtick text, .ytick text {{
        font-size: 0.75rem !important;
      }}
      .legendtitletext, .ytitle {{
        font-size: 1rem !important;
        font-weight: 600 !important;
      }}
      .legendtitletext {{
        transform: translateX(11px);
      }}
      .legendtext {{
        transform: translateX(-0.5rem);
      }}
      .plotly-notifier {{
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        border-radius: 1rem;
        transform: translateY(1rem);
      }}
      .plotly-notifier .notifier-note {{
        background-color: var(--mano-blue);
        color: var(--mano-offwhite);
        padding: 0.5rem 1rem;
        border-radius: 1rem;
      }}
    </style>
    """
  st.markdown(BRAND_CSS, unsafe_allow_html=True)