import streamlit as st
import folium
from streamlit_folium import st_folium
from volcano_models import VolcanoSimulation
from branca.element import MacroElement
from jinja2 import Template
import base64
import math
import numpy as np
from io import BytesIO
from PIL import Image

# ----------------------- Helpers -----------------------
def array_to_base64_png(array):
    img = Image.fromarray(array)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

# Cached simulation factory — only rebuilds when volcano/extent changes
@st.cache_resource(show_spinner=False)
def get_simulation(volcano_x, volcano_y, grid_res, extent_km):
    return VolcanoSimulation(
        volcano_x=volcano_x,
        volcano_y=volcano_y,
        grid_res=grid_res,
        extent_km=extent_km,
    )

# Cache only the raw spatial fields — alpha is applied at render time so
# magnitude/alert changes are always visible without cache interference
@st.cache_data(show_spinner=False)
def cached_damage_field(volcano_x, volcano_y, grid_res, extent_km, radius, max_radius):
    """Returns normalised damage field [0,1] — shape only, no intensity baked in."""
    sim = get_simulation(volcano_x, volcano_y, grid_res, extent_km)
    if radius <= 0 or max_radius <= 0:
        return np.zeros((grid_res, grid_res))
    inv_sq = 1.0 / (1.0 + (sim.dist_grid / max(radius, 1e-6)) ** 2)
    falloff_km = max(1.0, max_radius / 5.0)
    damage = inv_sq * np.exp(-sim.dist_grid / falloff_km)
    damage[sim.dist_grid > max_radius] = 0.0
    peak = damage.max()
    if peak > 1e-12:
        damage /= peak
    return damage

@st.cache_data(show_spinner=False)
def cached_ash_field(volcano_x, volcano_y, grid_res, extent_km,
                      radius, wind_dir, wind_speed, max_radius):
    """Returns normalised ash field [0,1] — shape only, no intensity baked in."""
    sim = get_simulation(volcano_x, volcano_y, grid_res, extent_km)
    _, field = sim.compute_ash_overlay(radius, wind_dir, wind_speed, max_radius, "white_gray_black")
    return field

def field_to_rgba(field, cmap_name, alpha_scale):
    """Convert a normalised field to RGBA uint8 with alpha_scale applied.
    Runs uncached every render so slider changes are immediately visible."""
    cmap = VolcanoSimulation.get_colormap(cmap_name)
    normed = field  # already [0,1]
    rgba = (cmap(normed) * 255).astype(np.uint8)
    base_alpha = np.clip(normed * 1.5, 0.0, 1.0)
    rgba[..., 3] = (base_alpha * float(np.clip(alpha_scale, 0.0, 1.0)) * 255).astype(np.uint8)
    return rgba

# ----------------------- Volcano Data -----------------------
volcanoes = [
    {"name": "Taal Volcano",          "lat": 14.0097, "lng": 120.9983, "status": "Active"},
    {"name": "Mayon Volcano",         "lat": 13.257,  "lng": 123.685,  "status": "Active"},
    {"name": "Pinatubo Volcano",      "lat": 15.142,  "lng": 120.349,  "status": "Active"},
    {"name": "Kanlaon Volcano",       "lat": 10.412,  "lng": 123.132,  "status": "Active"},
    {"name": "Bulusan Volcano",       "lat": 12.770,  "lng": 124.050,  "status": "Active"},
    {"name": "Mount Apo",             "lat": 6.987,   "lng": 125.255,  "status": "Potentially Active"},
    {"name": "Mount Pulag",           "lat": 16.611,  "lng": 120.889,  "status": "Inactive"},
    {"name": "Mount Arayat",          "lat": 15.200,  "lng": 120.742,  "status": "Potentially Active"},
    {"name": "Leonard Kniaseff",      "lat": 7.100,   "lng": 125.800,  "status": "Potentially Active"},
    {"name": "Cabalian",              "lat": 10.200,  "lng": 125.200,  "status": "Potentially Active"},
    {"name": "Isarog",                "lat": 13.600,  "lng": 123.400,  "status": "Potentially Active"},
    {"name": "Babuyan Claro",         "lat": 19.500,  "lng": 121.900,  "status": "Active"},
    {"name": "Biliran",               "lat": 11.520,  "lng": 124.530,  "status": "Active"},
    {"name": "Cagua",                 "lat": 18.220,  "lng": 122.120,  "status": "Active"},
    {"name": "Didicas",               "lat": 19.080,  "lng": 122.200,  "status": "Active"},
    {"name": "Iraya",                 "lat": 20.366,  "lng": 122.000,  "status": "Active"},
    {"name": "Matutum",               "lat": 6.350,   "lng": 125.070,  "status": "Active"},
    {"name": "Makaturing",            "lat": 7.650,   "lng": 124.300,  "status": "Active"},
    {"name": "Musuan",                "lat": 7.600,   "lng": 125.070,  "status": "Active"},
    {"name": "Parker",                "lat": 6.120,   "lng": 124.890,  "status": "Active"},
    {"name": "Ragang",                "lat": 7.700,   "lng": 124.500,  "status": "Active"},
    {"name": "Smith Volcano",         "lat": 19.525,  "lng": 121.913,  "status": "Active"},
    {"name": "Camiguin de Babuyanes", "lat": 19.300,  "lng": 121.900,  "status": "Active"},
    {"name": "Mount Everest",         "lat": 27.9881, "lng": 86.9250,  "status": "Inactive"},
    {"name": "Mount Fuji",            "lat": 35.3606, "lng": 138.7274, "status": "Active"},
    {"name": "Malabuyoc",             "lat": 9.6500,  "lng": 123.3167, "status": "Active"},
    {"name": "Ginatilan",             "lat": 9.5667,  "lng": 123.3667, "status": "Active"},
]

ALERT_LABELS  = ["🟢 Normal", "🔵 Abnormal", "🟡 Increasing Unrest", "🟠 Minor Eruption", "🔴 Hazardous Eruption"]
ALERT_RADIUS  = {0: 0, 1: 5, 2: 12, 3: 25, 4: 50}
ALERT_ZOOM    = {0: 11, 1: 11, 2: 10, 3: 9, 4: 8}
ALERT_GRIDRES = {0: 120, 1: 150, 2: 180, 3: 210, 4: 240}
# Scientifically grounded default magnitude per alert level (PHIVOLCS/USGS data):
# Level 0 → background micro-seismicity M0.3–1.5       → default M1.0
# Level 1 → low-level VT swarms M0.3–2.2 (Bulusan)    → default M2.0
# Level 2 → increasing VT/LF activity M2.0–3.5         → default M3.5
# Level 3 → intense seismicity pre-eruption M3–5        → default M4.5
# Level 4 → eruption-phase, can reach M5–6             → default M5.5
ALERT_EQ_DEFAULT = {0: 1.0, 1: 2.0, 2: 3.5, 3: 4.5, 4: 5.5}

ASH_CMAPS = {
    "🟠 Orange-Red (vivid)": "ash_orange",
    "🟡 Yellow (sulphur)":   "ash_yellow",
    "🔴 Hot":                "hot",
    "🌡 Yellow-Orange-Red":  "YlOrRd",
    "🌫 Grey (classic)":     "white_gray_black",
    "🟣 Plasma":             "plasma",
}

TILES = {
    "🌍 Hybrid (Google)":             {
        "url":  "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "attr": "Google Hybrid",
    },
    "🛰 Satellite (Google)":          {
        "url":  "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "attr": "Google Satellite",
    },
    "🛰 Satellite (Esri Clarity)":   {
        "url":  "https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri World Imagery Clarity",
    },
    "🗺 Street (OpenStreetMap)":      {
        "url":  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "© OpenStreetMap contributors",
    },
    "🛰 Satellite (Esri World Imagery)": {
        "url":  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles © Esri",
    },
}

DEFAULT_TILE = "🛰 Satellite (Esri World Imagery)"

# ----------------------- Session state -----------------------
if "active_tile" not in st.session_state:
    st.session_state.active_tile = DEFAULT_TILE
if "ash_cmap" not in st.session_state:
    st.session_state.ash_cmap = "🌫 Grey (classic)"

# ----------------------- Page Config -----------------------
st.set_page_config(layout="wide", page_title="VolcanoSim", page_icon="🌋")

st.markdown("""
<style>
.block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}
iframe {
    height: calc(100vh - 98px) !important;
    min-height: 400px;
    display: block;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
.sidebar-brand {
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    color: #ff4500;
    margin-bottom: 0.1rem;
}
.sidebar-sub { font-size: 0.75rem; color: #888; margin-bottom: 1rem; }
.sidebar-section {
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #aaa;
    text-transform: uppercase;
    margin: 1rem 0 0.3rem 0;
    border-top: 1px solid rgba(128,128,128,0.15);
    padding-top: 0.55rem;
}
.map-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 14px;
    background: rgba(0,0,0,0.05);
    border-bottom: 1px solid rgba(0,0,0,0.09);
}
.map-title { font-size: 1.05rem; font-weight: 800; display: flex; align-items: center; gap: 8px; }
.map-meta  { color: #777; font-size: 0.78rem; display: flex; gap: 14px; }
.stats-bar {
    display: flex;
    gap: 0;
    border-top: 1px solid rgba(0,0,0,0.07);
    background: rgba(0,0,0,0.03);
    font-size: 0.78rem;
}
.stat-cell {
    flex: 1;
    padding: 6px 14px;
    border-right: 1px solid rgba(0,0,0,0.07);
    display: flex;
    flex-direction: column;
    gap: 1px;
}
.stat-cell:last-child { border-right: none; }
.stat-label { font-size: 0.65rem; font-weight: 700; letter-spacing: .08em; color: #999; text-transform: uppercase; }
.stat-value { font-size: 0.92rem; font-weight: 700; color: #222; }
.stat-value.warn  { color: #c0392b; }
.stat-value.ok    { color: #27ae60; }
</style>
""", unsafe_allow_html=True)

# ----------------------- Sidebar -----------------------
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🌋 VolcanoSim</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Philippine Volcano Hazard Simulator</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">🗺 Volcano</div>', unsafe_allow_html=True)
    volcano_names = [vd["name"].strip() for vd in volcanoes]
    selected_name = st.selectbox("Select Volcano", volcano_names, label_visibility="collapsed")
    v = next(vd for vd in volcanoes if vd["name"].strip() == selected_name)
    status_icon = {"Active": "🔴", "Potentially Active": "🟡", "Inactive": "⚪"}.get(v["status"], "⚫")
    st.caption(f"{status_icon} {v['status']}  •  {v['lat']:.3f}°N, {v['lng']:.3f}°E")

    st.markdown('<div class="sidebar-section">⚠️ Alert Level</div>', unsafe_allow_html=True)
    alert_level = st.select_slider(
        "Alert Level", options=[0, 1, 2, 3, 4],
        format_func=lambda x: ALERT_LABELS[x], value=2,
        label_visibility="collapsed"
    )
    max_radius_km = ALERT_RADIUS[alert_level]
    zoom_level    = ALERT_ZOOM[alert_level]
    grid_res      = ALERT_GRIDRES[alert_level]
    st.caption(f"Hazard radius: **{max_radius_km} km**" if max_radius_km > 0 else "No active hazard zone")

    st.markdown('<div class="sidebar-section">🌍 Seismic Activity</div>', unsafe_allow_html=True)
    eq_default = ALERT_EQ_DEFAULT[alert_level]
    if st.session_state.get("last_alert_level") != alert_level:
        st.session_state["eq_magnitude"] = eq_default
        st.session_state["last_alert_level"] = alert_level
    eq_magnitude = st.slider(
        "Earthquake Magnitude", 0.0, 9.0,
        value=st.session_state.get("eq_magnitude", eq_default),
        step=0.1, format="M %.1f",
        key="eq_magnitude"
    )
    st.caption(f"Typical range for this level: M{eq_default - 1.0:.1f} – M{eq_default + 0.5:.1f}")

    st.markdown('<div class="sidebar-section">💨 Wind Conditions</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        wind_speed = st.number_input("Speed (km/h)", min_value=0, max_value=200, value=10, step=5)
    with c2:
        wind_dir = st.number_input("Direction (°)", min_value=0, max_value=359, value=90, step=5)
    ash_scale = st.slider("Ash Spread Scale", 0.1, 2.0, 1.0, 0.1)

    st.markdown('<div class="sidebar-section">🎨 Ash Appearance</div>', unsafe_allow_html=True)
    ash_cmap_label = st.selectbox(
        "Ash color", list(ASH_CMAPS.keys()),
        index=list(ASH_CMAPS.keys()).index(st.session_state.ash_cmap),
        label_visibility="collapsed"
    )
    st.session_state.ash_cmap = ash_cmap_label
    ash_cmap    = ASH_CMAPS[ash_cmap_label]
    ash_opacity = st.slider("Ash Opacity", 0.1, 1.0, 0.80, 0.05)

    st.markdown('<div class="sidebar-section">🗂 Layers</div>', unsafe_allow_html=True)
    show_ash    = st.toggle("Ash Plume",            value=True)
    show_damage = st.toggle("Damage Intensity",     value=True)
    show_rings  = st.toggle("Impact Rings (5 km)",  value=True)

    st.markdown('<div class="sidebar-section">🛰 Base Map</div>', unsafe_allow_html=True)
    tile_keys = list(TILES.keys())
    stored    = st.session_state.active_tile
    tile_idx  = tile_keys.index(stored) if stored in tile_keys else 0
    chosen_tile = st.radio(
        "Base map", tile_keys,
        index=tile_idx,
        label_visibility="collapsed",
    )
    st.session_state.active_tile = chosen_tile

# ----------------------- Simulation -----------------------
# Base radius — full hazard radius, not halved
radius = max_radius_km if max_radius_km > 0 else 0.1

# Extent grows with wind AND magnitude so overlays have room
wind_factor_extent = math.log1p(max(0.0, wind_speed) / 10.0)
quake_factor       = float(eq_magnitude / 9.0)
# High magnitude = much larger damage footprint
mag_radius_mult    = 1.0 + (quake_factor ** 1.2) * 3.0  # M9→4x, M5→1.8x, M1→1.1x
extent_km = max(30, int(max_radius_km * max(2.0, 2.0 + wind_factor_extent) * min(mag_radius_mult, 3.0)))

sim = get_simulation(v["lng"], v["lat"], grid_res, extent_km)

# ---- Damage physics ----
# Alert level sets the BASE hazard zone size
# Magnitude independently controls: spread radius + visual intensity
# At M8.9 the damage should be huge and vivid regardless of alert level
dmg_radius    = radius * mag_radius_mult
effective_max = max_radius_km * mag_radius_mult

# Alpha: magnitude is the primary driver (0.1→1.0 across M0→M9)
# Alert level gives a small floor boost so higher alerts always look worse
alert_boost   = 0.15 * float(alert_level / 4.0)
dmg_alpha     = float(np.clip(quake_factor ** 0.6 + alert_boost, 0.0, 1.0))

if show_damage and max_radius_km > 0:
    dmg_field = cached_damage_field(
        v["lng"], v["lat"], grid_res, extent_km,
        dmg_radius, effective_max
    )
    dmg_rgba = field_to_rgba(dmg_field, "violet_yellow", dmg_alpha)
else:
    dmg_field = None
    dmg_rgba  = None

# ---- Ash physics ----
if show_ash and max_radius_km > 0:
    ash_field = cached_ash_field(
        v["lng"], v["lat"], grid_res, extent_km,
        radius * ash_scale, wind_dir, wind_speed, max_radius_km
    )
    ash_intensity = float(np.clip(
        (radius * ash_scale) / max(max_radius_km, 1e-6) * 1.4 + 0.1, 0.0, 1.0
    ))
    ash_rgba = field_to_rgba(ash_field, ash_cmap, ash_intensity)
else:
    ash_field = None
    ash_rgba  = None

# ----------------------- Stats computation -----------------------
damage_area_km2 = 0.0
ash_area_km2    = 0.0
if dmg_field is not None and max_radius_km > 0:
    damage_area_km2 = sim.compute_affected_area_km2(dmg_field, threshold=0.15)
if ash_field is not None and max_radius_km > 0:
    ash_area_km2 = sim.compute_affected_area_km2(ash_field, threshold=0.10)

total_hazard_area = math.pi * max_radius_km ** 2

# ----------------------- Map -----------------------
tile_cfg  = TILES[st.session_state.active_tile]
tile_url  = tile_cfg["url"]
tile_attr = tile_cfg["attr"]

m = folium.Map(
    location=[v["lat"], v["lng"]],
    zoom_start=zoom_level,
    control_scale=True,
    tiles=tile_url,
    attr=tile_attr,
)

# Volcano markers
for vdata in volcanoes:
    icon_color  = {"Active": "red", "Potentially Active": "orange", "Inactive": "blue"}.get(vdata["status"], "gray")
    is_selected = vdata["name"].strip() == selected_name
    folium.Marker(
        location=[vdata["lat"], vdata["lng"]],
        popup=folium.Popup(f"<b>{vdata['name'].strip()}</b><br>{vdata['status']}", max_width=200),
        tooltip=vdata["name"].strip(),
        icon=folium.Icon(color=icon_color, icon="fire" if is_selected else "info-sign", prefix="glyphicon")
    ).add_to(m)

# Hazard boundary
if show_damage and max_radius_km > 0:
    folium.Circle(
        location=[v["lat"], v["lng"]], radius=max_radius_km * 1000,
        color="#ff6600", weight=2, fill=True, fill_color="#ff6600",
        fill_opacity=0.07, tooltip=f"Hazard boundary: {max_radius_km} km"
    ).add_to(m)

# Damage overlay
if show_damage and dmg_rgba is not None:
    folium.raster_layers.ImageOverlay(
        image=array_to_base64_png(dmg_rgba),
        bounds=[[sim.lat_min, sim.lon_min], [sim.lat_max, sim.lon_max]],
        opacity=0.75, name="Damage Intensity"
    ).add_to(m)

# Ash overlay
if show_ash and ash_rgba is not None:
    folium.raster_layers.ImageOverlay(
        image=array_to_base64_png(ash_rgba),
        bounds=[[sim.lat_min, sim.lon_min], [sim.lat_max, sim.lon_max]],
        opacity=ash_opacity, name="Ash Plume"
    ).add_to(m)

# Impact rings
if show_rings and max_radius_km > 0:
    for r_m in range(5000, max_radius_km * 1000 + 1, 5000):
        folium.Circle(
            location=[v["lat"], v["lng"]], radius=r_m,
            color="#cc44ff", fill=False, dash_array="6,4",
            weight=1.2, opacity=0.55, tooltip=f"{r_m // 1000} km radius"
        ).add_to(m)

# ----------------------- Legend -----------------------
class FloatLegend(MacroElement):
    def __init__(self, html):
        super().__init__()
        self._template = Template("""
        {% macro html(this, kwargs) %}
        """ + html + """
        {% endmacro %}
        """)

m.add_child(FloatLegend("""
<div style='
    position:fixed;bottom:28px;left:28px;
    background:rgba(12,12,18,0.90);
    border:1px solid rgba(255,255,255,0.12);
    border-radius:10px;
    padding:12px 16px;
    z-index:9999;
    font-family:monospace;
    font-size:12px;
    color:#eee;
    min-width:175px;
    backdrop-filter:blur(6px);
'>
  <div style='font-weight:700;font-size:13px;margin-bottom:9px;color:#ff6a00;'>&#127755; Legend</div>
  <div style='font-size:10px;color:#aaa;font-weight:700;letter-spacing:.08em;margin-bottom:5px;'>DAMAGE INTENSITY</div>
  <div style='display:flex;align-items:center;gap:7px;margin-bottom:3px;'><span style='background:#ffff00;width:15px;height:9px;display:inline-block;border-radius:2px;'></span>Low</div>
  <div style='display:flex;align-items:center;gap:7px;margin-bottom:3px;'><span style='background:#ffa500;width:15px;height:9px;display:inline-block;border-radius:2px;'></span>Moderate</div>
  <div style='display:flex;align-items:center;gap:7px;margin-bottom:3px;'><span style='background:#ff0000;width:15px;height:9px;display:inline-block;border-radius:2px;'></span>High</div>
  <div style='display:flex;align-items:center;gap:7px;margin-bottom:10px;'><span style='background:#800080;width:15px;height:9px;display:inline-block;border-radius:2px;'></span>Severe</div>
  <div style='font-size:10px;color:#aaa;font-weight:700;letter-spacing:.08em;margin-bottom:5px;'>VOLCANO STATUS</div>
  <div style='display:flex;align-items:center;gap:7px;margin-bottom:3px;'><span style='color:#e74c3c;font-size:14px;'>&#9679;</span>Active</div>
  <div style='display:flex;align-items:center;gap:7px;margin-bottom:3px;'><span style='color:#f39c12;font-size:14px;'>&#9679;</span>Potentially Active</div>
  <div style='display:flex;align-items:center;gap:7px;'><span style='color:#5dade2;font-size:14px;'>&#9679;</span>Inactive</div>
</div>
"""))

# ----------------------- Header bar -----------------------
st.markdown(f"""
<div class="map-header">
  <div class="map-title">
    &#127755; {selected_name}
    <span style='font-size:0.82rem;font-weight:400;color:#666;'>{ALERT_LABELS[alert_level]}</span>
  </div>
  <div class="map-meta">
    <span>&#128168; {wind_speed} km/h @ {wind_dir}&deg;</span>
    <span>&#128207; {max_radius_km} km radius</span>
    <span>&#128243; M{eq_magnitude:.1f}</span>
    <span style='font-size:0.75rem;color:#aaa;border:1px solid #ddd;border-radius:4px;padding:1px 6px;'>{st.session_state.active_tile}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ----------------------- Map render -----------------------
st_folium(m, use_container_width=True, height=820, returned_objects=[])

# ----------------------- Stats bar -----------------------
if max_radius_km > 0:
    dmg_pct  = min(100.0, damage_area_km2 / max(total_hazard_area, 1) * 100)
    ash_pct  = min(100.0, ash_area_km2    / max(total_hazard_area, 1) * 100)
    sev_cls  = "warn" if alert_level >= 3 else ("" if alert_level >= 2 else "ok")
    ash_cls  = "warn" if ash_area_km2 > 500 else ""

    st.markdown(f"""
    <div class="stats-bar">
      <div class="stat-cell">
        <div class="stat-label">&#128207; Hazard Zone</div>
        <div class="stat-value">{total_hazard_area:,.0f} km²</div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">&#128293; Damage Area</div>
        <div class="stat-value {sev_cls}">{damage_area_km2:,.0f} km² <span style='font-size:0.7rem;font-weight:400;color:#999;'>({dmg_pct:.0f}% of zone)</span></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">&#127787; Ash Fall Area</div>
        <div class="stat-value {ash_cls}">{ash_area_km2:,.0f} km² <span style='font-size:0.7rem;font-weight:400;color:#999;'>({ash_pct:.0f}% of zone)</span></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">&#127774; Max Ash Reach</div>
        <div class="stat-value">{max_radius_km * 1.5:.0f} km <span style='font-size:0.7rem;font-weight:400;color:#999;'>downwind</span></div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">&#128204; Alert Level</div>
        <div class="stat-value {sev_cls}">{ALERT_LABELS[alert_level]}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="stats-bar">
      <div class="stat-cell">
        <div class="stat-label">Status</div>
        <div class="stat-value ok">&#127822; No active hazard — monitoring only</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
