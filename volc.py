import streamlit as st
import folium
from streamlit_folium import st_folium
from volcano_models import VolcanoSimulation
from branca.element import MacroElement
from jinja2 import Template
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# ----------------------- Volcano Data -----------------------
volcanoes = [
    {"name": "Taal Volcano", "lat": 14.002, "lng": 120.997, "status": "Active"},
    {"name": "Mayon Volcano", "lat": 13.257, "lng": 123.685, "status": "Active"},
    {"name": "Pinatubo Volcano", "lat": 15.142, "lng": 120.349, "status": "Active"},
    {"name": "Kanlaon Volcano", "lat": 10.412, "lng": 123.132, "status": "Active"},
    {"name": "Bulusan Volcano", "lat": 12.770, "lng": 124.050, "status": "Active"},
    {"name": "Mount Apo", "lat": 6.987, "lng": 125.255, "status": "Potentially Active"},
    {"name": "Mount Pulag", "lat": 16.611, "lng": 120.889, "status": "Inactive"},
    {"name": "Mount Arayat", "lat": 15.200, "lng": 120.742, "status": "Potentially Active"},
    {"name": "Leonard Kniaseff", "lat": 7.100, "lng": 125.800, "status": "Potentially Active"},
    {"name": "Cabalian", "lat": 10.200, "lng": 125.200, "status": "Potentially Active"},
    {"name": "Isarog", "lat": 13.600, "lng": 123.400, "status": "Potentially Active"},
    {"name": "Babuyan Claro", "lat": 19.500, "lng": 121.900, "status": "Active"},
    {"name": "Biliran", "lat": 11.520, "lng": 124.530, "status": "Active"},
    {"name": "Cagua", "lat": 18.220, "lng": 122.120, "status": "Active"},
    {"name": "Didicas", "lat": 19.080, "lng": 122.200, "status": "Active"},
    {"name": "Iraya", "lat": 20.366, "lng": 122.000, "status": "Active"},
    {"name": "Matutum", "lat": 6.350, "lng": 125.070, "status": "Active"},
    {"name": "Makaturing", "lat": 7.650, "lng": 124.300, "status": "Active"},
    {"name": "Musuan", "lat": 7.600, "lng": 125.070, "status": "Active"},
    {"name": "Parker", "lat": 6.120, "lng": 124.890, "status": "Active"},
    {"name": "Ragang", "lat": 7.700, "lng": 124.500, "status": "Active"},
    {"name": "Smith Volcano", "lat": 19.525, "lng": 121.913, "status": "Active"},
    {"name": "Camiguin de Babuyanes", "lat": 19.300, "lng": 121.900, "status": "Active"},
]

# ----------------------- Sidebar Controls -----------------------
st.set_page_config(layout="wide")
st.sidebar.header("⚙️ Simulation Controls")
volcano_names = [v["name"] for v in volcanoes]
selected_volcano = st.sidebar.selectbox("Select Volcano", volcano_names)

alert_level = st.sidebar.radio(
    "Alert Level",
    [0, 1, 2, 3, 4],
    format_func=lambda x: ["Normal", "Abnormal", "Increasing Unrest", "Minor Eruption", "Hazardous Eruption"][x],
    index=2
)
wind_speed = st.sidebar.slider("Wind Speed (km/h)", 0, 50, 10)
wind_dir = st.sidebar.slider("Wind Direction (°)", 0, 360, 90)
ash_scale = st.sidebar.slider("Ash Scale", 0.1, 2.0, 1.0)
show_ash = st.sidebar.checkbox("Show Ash Plume", value=True)
show_damage = st.sidebar.checkbox("Show Damage Map", value=True)
show_rings = st.sidebar.checkbox("Show Impact Rings", value=True)

# ----------------------- Simulation Setup -----------------------
v = next(v for v in volcanoes if v["name"] == selected_volcano)
sim = VolcanoSimulation(volcano_x=v["lng"], volcano_y=v["lat"])
settings = {0: {"max_radius": 0}, 1: {"max_radius": 5}, 2: {"max_radius": 12}, 3: {"max_radius": 25}, 4: {"max_radius": 50}}[alert_level]
radius = settings["max_radius"] / 2 if settings["max_radius"] > 0 else 0.1

# ----------------------- Map Setup -----------------------
m = folium.Map(location=[v["lat"], v["lng"]], zoom_start=9, control_scale=True)

# Volcano markers
for vdata in volcanoes:
    status = vdata["status"]
    icon_color = "red" if status == "Active" else "orange" if status == "Potentially Active" else "blue"
    folium.Marker(
        location=[vdata["lat"], vdata["lng"]],
        popup=f"{vdata['name']} ({status})",
        icon=folium.Icon(color=icon_color)
    ).add_to(m)

# Hazard zone
if show_damage:
    folium.Circle(
        location=[v["lat"], v["lng"]],
        radius=settings["max_radius"] * 1000,
        color="orange",
        fill=True,
        fill_opacity=0.3,
        popup=f"Hazard zone: {selected_volcano}"
    ).add_to(m)

# Damage overlay
if show_damage:
    dmg_img = sim.compute_damage_overlay(
        radius,
        scale=alert_level,
        eq_mag_num=3.0,
        max_radius=settings["max_radius"],
        cmap_name="violet_yellow"
    )
    folium.raster_layers.ImageOverlay(
        image=dmg_img,
        bounds=[[sim.y_min, sim.x_min], [sim.y_max, sim.x_max]],
        opacity=0.85
    ).add_to(m)

# Ash overlay
if show_ash:
    ash_img = sim.compute_ash_overlay(
        radius,
        wind_dir,
        wind_speed,
        settings["max_radius"],
        cmap_name="white_gray_black"
    )
    folium.raster_layers.ImageOverlay(
        image=ash_img,
        bounds=[[sim.y_min, sim.x_min], [sim.y_max, sim.x_max]],
        opacity=0.7
    ).add_to(m)

# Impact rings
if show_rings:
    for r in range(5000, settings["max_radius"] * 1000, 5000):
        folium.Circle(
            location=[v["lat"], v["lng"]],
            radius=r,
            color="purple",
            fill=False,
            dash_array="5,5",
            opacity=0.5
        ).add_to(m)

# ----------------------- Legends -----------------------
class FloatLegend(MacroElement):
    def __init__(self, html):
        super().__init__()
        self._template = Template(f"""
        {{% macro html(this, kwargs) %}}
        {html}
        {{% endmacro %}}
        """)

legend_damage_html = """
<div style='position: fixed; bottom: 30px; left: 30px; width: 160px; height: 140px;
     background-color: white; z-index:9999; font-size:14px;
     border:2px solid grey; padding: 10px;'>
<b>Damage Intensity</b><br>
<span style='background:#ffff00;width:20px;height:10px;display:inline-block;'></span> Low<br>
<span style='background:#ffa500;width:20px;height:10px;display:inline-block;'></span> Moderate<br>
<span style='background:#ff0000;width:20px;height:10px;display:inline-block;'></span> High<br>
<span style='background:#800080;width:20px;height:10px;display:inline-block;'></span> Severe
</div>
"""

legend_ash_html = """
<div style='position: fixed; bottom: 30px; right: 30px; width: 160px; height: 100px;
     background-color: white; z-index:9999; font-size:14px;
     border:2px solid grey; padding: 10px;'>
<b>Ash Intensity</b><br>
<span style='background:#ffffff;width:20px;height:10px;display:inline-block;'></span> Light<br>
<span style='background:#888888;width:20px;height:10px;display:inline-block;'></span> Moderate<br>
<span style='background:#000000;width:20px;height:10px;display:inline-block;'></span> Dense
</div>
"""

m.add_child(FloatLegend(legend_damage_html))
m.add_child(FloatLegend(legend_ash_html))

# ----------------------- Colorbar for Damage Overlay -----------------------
def make_colorbar(cmap_name="violet_yellow", vmin=0, vmax=1, label="Damage Intensity"):
    fig, ax = plt.subplots(figsize=(0.4, 3))
    norm = plt.Normalize(vmin=vmin, vmax=vmax)

    # ✅ Use centralized colormap from volcano_models
    cmap = VolcanoSimulation.get_colormap(cmap_name)

    fig.subplots_adjust(right=0.5)
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=ax)
    cb.set_label(label)

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    return f"<img src='data:image/png;base64,{b64}' style='position: fixed; top: 30px; right: 30px; z-index:9999; height:200px;'>"

colorbar_html = make_colorbar(cmap_name="violet_yellow", vmin=0, vmax=1, label="Damage Intensity")
m.get_root().html.add_child(folium.Element(colorbar_html))

# ----------------------- Render Map -----------------------
st_folium(m, width=-1, height=1000)