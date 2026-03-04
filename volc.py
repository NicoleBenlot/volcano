import streamlit as st
import folium
from streamlit_folium import st_folium
from volcano_models import VolcanoSimulation
from branca.element import MacroElement
from jinja2 import Template
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from PIL import Image

# ----------------------- Helpers -----------------------
def array_to_base64_png(array):
    img = Image.fromarray(array)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def make_colorbar(cmap_name="violet_yellow", vmin=0, vmax=1, label=""):
    fig, ax = plt.subplots(figsize=(0.35, 2.8))
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    cmap = VolcanoSimulation.get_colormap(cmap_name)
    fig.subplots_adjust(right=0.5)
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=ax)
    cb.set_label(label, fontsize=8)
    cb.ax.tick_params(labelsize=7)
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{b64}"

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

ALERT_LABELS = ["🟢 Normal", "🔵 Abnormal", "🟡 Increasing Unrest", "🟠 Minor Eruption", "🔴 Hazardous Eruption"]
ALERT_RADIUS = {0: 0, 1: 5, 2: 12, 3: 25, 4: 50}

# ----------------------- Page Config -----------------------
st.set_page_config(layout="wide", page_title="🌋 Volcano Simulation", page_icon="🌋")

st.markdown("""
<style>
/* Sidebar header branding */
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}
.sidebar-brand {
    font-size: 1.4rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    color: #ff4500;
    margin-bottom: 0.2rem;
}
.sidebar-sub {
    font-size: 0.78rem;
    color: #888;
    margin-bottom: 1.2rem;
}
/* Alert badge */
.alert-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.85rem;
    margin-top: 4px;
}
/* Section dividers */
.sidebar-section {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #aaa;
    text-transform: uppercase;
    margin: 1.1rem 0 0.4rem 0;
}
</style>
""", unsafe_allow_html=True)

# ----------------------- Sidebar -----------------------
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🌋 VolcanoSim</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Philippine Volcano Hazard Simulator</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">🗺 Volcano Selection</div>', unsafe_allow_html=True)
    volcano_names = [v["name"].strip() for v in volcanoes]
    selected_name = st.selectbox("Select Volcano", volcano_names, label_visibility="collapsed")

    v = next(vd for vd in volcanoes if vd["name"].strip() == selected_name)
    status_color = {"Active": "🔴", "Potentially Active": "🟡", "Inactive": "⚪"}.get(v["status"], "⚫")
    st.caption(f"{status_color} {v['status']}  •  {v['lat']:.3f}°N, {v['lng']:.3f}°E")

    st.markdown('<div class="sidebar-section">⚠️ Alert Level</div>', unsafe_allow_html=True)
    alert_level = st.select_slider(
        "Alert Level",
        options=[0, 1, 2, 3, 4],
        format_func=lambda x: ALERT_LABELS[x],
        value=2,
        label_visibility="collapsed"
    )
    max_radius_km = ALERT_RADIUS[alert_level]
    if max_radius_km > 0:
        st.caption(f"Hazard radius: **{max_radius_km} km**")
    else:
        st.caption("No active hazard zone")

    st.markdown('<div class="sidebar-section">💨 Wind Conditions</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        wind_speed = st.number_input("Speed (km/h)", min_value=0, max_value=200, value=10, step=5)
    with col2:
        wind_dir = st.number_input("Direction (°)", min_value=0, max_value=360, value=90, step=5)
    ash_scale = st.slider("Ash Spread Scale", 0.1, 2.0, 1.0, 0.1)

    st.markdown('<div class="sidebar-section">🗂 Layer Visibility</div>', unsafe_allow_html=True)
    show_ash    = st.toggle("Ash Plume", value=True)
    show_damage = st.toggle("Damage Intensity", value=True)
    show_rings  = st.toggle("Impact Rings (5 km)", value=True)

# ----------------------- Simulation -----------------------
radius = max_radius_km / 2 if max_radius_km > 0 else 0.1
extent_km = max(20, int(max_radius_km * 1.8))

sim = VolcanoSimulation(
    volcano_x=v["lng"],
    volcano_y=v["lat"],
    grid_res=240,
    extent_km=extent_km
)

# ----------------------- Map -----------------------
m = folium.Map(location=[v["lat"], v["lng"]], zoom_start=9, control_scale=True, tiles=None)

folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri World Imagery',
    name='Satellite',
    overlay=False,
    control=True
).add_to(m)

folium.TileLayer('OpenStreetMap', name='Street Map', overlay=False, control=True).add_to(m)

# Volcano markers
for vdata in volcanoes:
    icon_color = {"Active": "red", "Potentially Active": "orange", "Inactive": "blue"}.get(vdata["status"], "gray")
    is_selected = vdata["name"].strip() == selected_name
    folium.Marker(
        location=[vdata["lat"], vdata["lng"]],
        popup=folium.Popup(f"<b>{vdata['name']}</b><br>{vdata['status']}", max_width=200),
        tooltip=vdata["name"].strip(),
        icon=folium.Icon(color=icon_color, icon="fire" if is_selected else "info-sign", prefix="glyphicon")
    ).add_to(m)

# Hazard zone boundary
if show_damage and max_radius_km > 0:
    folium.Circle(
        location=[v["lat"], v["lng"]],
        radius=max_radius_km * 1000,
        color="#ff6600",
        weight=2,
        fill=True,
        fill_color="#ff6600",
        fill_opacity=0.08,
        tooltip=f"Hazard boundary: {max_radius_km} km"
    ).add_to(m)

# Damage overlay
if show_damage:
    dmg_img = sim.compute_damage_overlay(
        radius, scale=alert_level, eq_mag_num=3.0,
        max_radius=max_radius_km, cmap_name="inferno"
    )
    folium.raster_layers.ImageOverlay(
        image=array_to_base64_png(dmg_img),
        bounds=[[sim.lat_min, sim.lon_min], [sim.lat_max, sim.lon_max]],
        opacity=0.75,
        name="Damage Intensity"
    ).add_to(m)

# Ash overlay
if show_ash:
    ash_img = sim.compute_ash_overlay(
        radius * ash_scale, wind_dir, wind_speed,
        max_radius=max_radius_km, cmap_name="Greys"
    )
    folium.raster_layers.ImageOverlay(
        image=array_to_base64_png(ash_img),
        bounds=[[sim.lat_min, sim.lon_min], [sim.lat_max, sim.lon_max]],
        opacity=0.70,
        name="Ash Plume"
    ).add_to(m)

# Impact rings
if show_rings and max_radius_km > 0:
    for r_m in range(5000, max_radius_km * 1000 + 1, 5000):
        folium.Circle(
            location=[v["lat"], v["lng"]],
            radius=r_m,
            color="#cc44ff",
            fill=False,
            dash_array="6,4",
            weight=1.2,
            opacity=0.55,
            tooltip=f"{r_m // 1000} km radius"
        ).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# ----------------------- Map Legend (combined, single block) -----------------------
class FloatLegend(MacroElement):
    def __init__(self, html):
        super().__init__()
        self._template = Template(f"""
        {{% macro html(this, kwargs) %}}
        {html}
        {{% endmacro %}}
        """)

legend_html = """
<div style='
    position: fixed; bottom: 28px; left: 28px;
    background: rgba(15,15,20,0.88);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 10px;
    padding: 12px 16px;
    z-index: 9999;
    font-family: monospace;
    font-size: 12px;
    color: #eee;
    min-width: 170px;
    backdrop-filter: blur(4px);
'>
  <div style='font-weight:700; font-size:13px; margin-bottom:8px; color:#ff6a00;'>🌋 Legend</div>
  <div style='margin-bottom:6px; font-size:11px; color:#aaa; font-weight:600;'>DAMAGE INTENSITY</div>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:3px;'>
    <span style='background:#ffff00;width:16px;height:10px;display:inline-block;border-radius:2px;'></span> Low
  </div>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:3px;'>
    <span style='background:#ffa500;width:16px;height:10px;display:inline-block;border-radius:2px;'></span> Moderate
  </div>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:3px;'>
    <span style='background:#ff0000;width:16px;height:10px;display:inline-block;border-radius:2px;'></span> High
  </div>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;'>
    <span style='background:#800080;width:16px;height:10px;display:inline-block;border-radius:2px;'></span> Severe
  </div>
  <div style='margin-bottom:6px; font-size:11px; color:#aaa; font-weight:600;'>VOLCANO STATUS</div>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:3px;'>
    <span style='color:#e74c3c;font-size:14px;'>📍</span> Active
  </div>
  <div style='display:flex;align-items:center;gap:8px;margin-bottom:3px;'>
    <span style='color:#f39c12;font-size:14px;'>📍</span> Potentially Active
  </div>
  <div style='display:flex;align-items:center;gap:8px;'>
    <span style='color:#3498db;font-size:14px;'>📍</span> Inactive
  </div>
</div>
"""
m.add_child(FloatLegend(legend_html))

# ----------------------- Render -----------------------
st.markdown(f"""
<div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:0.5rem;'>
  <div>
    <span style='font-size:1.5rem; font-weight:800;'>🌋 {selected_name}</span>
    <span style='margin-left:12px; font-size:0.9rem; color:#888;'>{ALERT_LABELS[alert_level]}</span>
  </div>
  <div style='font-size:0.8rem; color:#888;'>
    Wind: {wind_speed} km/h @ {wind_dir}° &nbsp;|&nbsp; Radius: {max_radius_km} km
  </div>
</div>
""", unsafe_allow_html=True)

st_folium(m, width="100%", height=820, returned_objects=[])
