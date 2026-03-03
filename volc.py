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
import io

def array_to_base64_png(array):
    img = Image.fromarray(array)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

# ----------------------- Volcano Data -----------------------
volcanoes = [
    {"name": "Taal Volcano", "lat": 14.0097, "lng": 120.9983, "status": "Active"},
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
    {"name": "Mount Everest", "lat": 27.9881, "lng": 86.9250, "status": "Inactive"},
    {"name": "Mount Fuji", "lat": 35.3606, "lng": 138.7274, "status": "Active"},
    {"name": " Malabuyoc", "lat": 9.6500, "lng": 123.3167, "status": "Active"},
    {"name": " Ginatilan", "lat": 9.5667, "lng": 123.3667, "status": "Active"},
    {"name": "Mauna Loa", "lat": 19.4756, "lng": -155.6081, "status": "Active"},
    {"name": "Kilauea", "lat": 19.4210, "lng": -155.2870, "status": "Active"},
    {"name": "Mount St. Helens", "lat": 46.1912, "lng": -122.1944, "status": "Active"},
    {"name": "Mount Rainier", "lat": 46.8523, "lng": -121.7603, "status": "Active"},
    {"name": "Popocatepetl", "lat": 19.0230, "lng": -98.6220, "status": "Active"},
    {"name": "Cotopaxi", "lat": -0.6800, "lng": -78.4370, "status": "Active"},
    {"name": "Mount Etna", "lat": 37.7510, "lng": 14.9934, "status": "Active"},
    {"name": "Vesuvius", "lat": 40.8214, "lng": 14.4265, "status": "Active"},
    {"name": "Krakatoa", "lat": -6.1020, "lng": 105.4230, "status": "Active"},
    {"name": "Mount Fuji", "lat": 35.3606, "lng": 138.7274, "status": "Active"},
    {"name": "Merapi", "lat": -7.5407, "lng": 110.4462, "status": "Active"},
    {"name": "Mayon", "lat": 13.2570, "lng": 123.6850, "status": "Active"},
    {"name": "Pinatubo", "lat": 15.1429, "lng": 120.3496, "status": "Active"},
    {"name": "Eyjafjallajokull", "lat": 63.6330, "lng": -19.6200, "status": "Active"},
    {"name": "Stromboli", "lat": 38.7890, "lng": 15.2130, "status": "Active"},
     {"name": "Nevado del Ruiz", "lat": 4.8920, "lng": -75.3240, "status": "Active"},
  {"name": "Galeras", "lat": 1.2210, "lng": -77.3580, "status": "Active"},
  {"name": "Sakurajima", "lat": 31.5850, "lng": 130.6570, "status": "Active"},
  {"name": "Aso", "lat": 32.8840, "lng": 131.1040, "status": "Active"},
  {"name": "Tambora", "lat": -8.2470, "lng": 118.0000, "status": "Active"},
  {"name": "Taal", "lat": 14.0020, "lng": 120.9930, "status": "Active"},
  {"name": "Hekla", "lat": 63.9830, "lng": -19.7000, "status": "Active"},
  {"name": "Katla", "lat": 63.6330, "lng": -19.0500, "status": "Active"},
  {"name": "Nyiragongo", "lat": -1.5200, "lng": 29.2500, "status": "Active"},
  {"name": "Nyamuragira", "lat": -1.4080, "lng": 29.2000, "status": "Active"},
  {"name": "Mount Cameroon", "lat": 4.2030, "lng": 9.1700, "status": "Active"},
  {"name": "Teide", "lat": 28.2720, "lng": -16.6420, "status": "Active"},
  {"name": "Ruapehu", "lat": -39.2800, "lng": 175.5700, "status": "Active"},
  {"name": "White Island", "lat": -37.5200, "lng": 177.1800, "status": "Active"},
  {"name": "Shiveluch", "lat": 56.6530, "lng": 161.3600, "status": "Active"},
  {"name": "Klyuchevskoy", "lat": 56.0560, "lng": 160.6420, "status": "Active"},
  {"name": "Pacaya", "lat": 14.3820, "lng": -90.6010, "status": "Active"},
  {"name": "Fuego", "lat": 14.4730, "lng": -90.8800, "status": "Active"},
  {"name": "Mount Hood", "lat": 45.3730, "lng": -121.6950, "status": "Active"},
  {"name": "Mount Redoubt", "lat": 60.4850, "lng": -152.7420, "status": "Active"},
     {"name": "Anak Krakatau", "lat": -6.1020, "lng": 105.4230, "status": "Active"},
  {"name": "Agung", "lat": -8.3430, "lng": 115.5080, "status": "Active"},
  {"name": "Semeru", "lat": -8.1080, "lng": 112.9220, "status": "Active"},
  {"name": "Bromo", "lat": -7.9420, "lng": 112.9530, "status": "Active"},
  {"name": "Kerinci", "lat": -1.6970, "lng": 101.2640, "status": "Active"},
  {"name": "Sinabung", "lat": 3.1700, "lng": 98.3920, "status": "Active"},
  {"name": "Ulawun", "lat": -5.0500, "lng": 151.3300, "status": "Active"},
  {"name": "Manam", "lat": -4.0800, "lng": 145.0370, "status": "Active"},
  {"name": "Bagana", "lat": -6.1370, "lng": 155.1960, "status": "Active"},
  {"name": "Yasur", "lat": -19.5320, "lng": 169.4470, "status": "Active"},
  {"name": "Piton de la Fournaise", "lat": -21.2440, "lng": 55.7080, "status": "Active"},
  {"name": "La Soufriere (St. Vincent)", "lat": 13.3300, "lng": -61.1800, "status": "Active"},
  {"name": "Soufriere Hills", "lat": 16.7200, "lng": -62.1800, "status": "Active"},
  {"name": "Santa Maria", "lat": 14.7570, "lng": -91.5520, "status": "Active"},
  {"name": "Tungurahua", "lat": -1.4670, "lng": -78.4420, "status": "Active"},
  {"name": "Villarrica", "lat": -39.4200, "lng": -71.9300, "status": "Active"},
  {"name": "Llaima", "lat": -38.6920, "lng": -71.7290, "status": "Active"},
  {"name": "Colima", "lat": 19.5140, "lng": -103.6200, "status": "Active"},
  {"name": "Paricutin", "lat": 19.4930, "lng": -102.2510, "status": "Dormant"},
  {"name": "Mount Erebus", "lat": -77.5300, "lng": 167.1700, "status": "Active"}
]

# ----------------------- Sidebar Controls -----------------------
st.set_page_config(layout="wide", page_title="Volcano Simulation")
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

st.sidebar.markdown("---")
st.sidebar.subheader("🗺️ Map Appearance")
#map_opacity = st.sidebar.slider("Background Sat Opacity", 0.0, 1.0, 1.0)
show_ash = st.sidebar.checkbox("Show Ash Plume", value=True)
show_damage = st.sidebar.checkbox("Show Damage Map", value=True)
show_rings = st.sidebar.checkbox("Show Impact Rings", value=True)

# ----------------------- Simulation Setup -----------------------
v = next(v for v in volcanoes if v["name"] == selected_volcano)
settings = {0: {"max_radius": 0}, 1: {"max_radius": 5}, 2: {"max_radius": 12}, 3: {"max_radius": 25}, 4: {"max_radius": 50}}[alert_level]
max_radius_km = settings["max_radius"]
radius = max_radius_km / 2 if max_radius_km > 0 else 0.1

extent_km = max(20, int(max_radius_km * 1.8))

sim = VolcanoSimulation(
    volcano_x=v["lng"],
    volcano_y=v["lat"],
    grid_res=240,
    extent_km=extent_km
)

# ----------------------- Map Setup -----------------------
# Initialize map without default tiles so we can control layers
m = folium.Map(location=[v["lat"], v["lng"]], zoom_start=9, control_scale=True, tiles=None)

# Add Satellite Layer (Esri)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satellite View',
    #opacity=map_opacity,
    overlay=False,
    control=True
).add_to(m)

# Add Standard Street View Layer
#folium.TileLayer('OpenStreetMap', name='Street View', overlay=False).add_to(m)

# Volcano markers
for vdata in volcanoes:
    status = vdata["status"]
    icon_color = "red" if status == "Active" else "orange" if status == "Potentially Active" else "blue"
    folium.Marker(
        location=[vdata["lat"], vdata["lng"]],
        popup=f"{vdata['name']} ({status})",
        icon=folium.Icon(color=icon_color)
    ).add_to(m)

# Hazard zone circle
if show_damage and max_radius_km > 0:
    folium.Circle(
        location=[v["lat"], v["lng"]],
        radius=max_radius_km * 1000,
        color="orange",
        fill=True,
        fill_opacity=0.3,
        popup=f"Hazard zone: {selected_volcano}"
    ).add_to(m)

# ----------------------- Overlays -----------------------

# Damage overlay
if show_damage:
    dmg_img = sim.compute_damage_overlay(
        radius,
        scale=alert_level,
        eq_mag_num=3.0,
        max_radius=max_radius_km,
        cmap_name="inferno"
    )
    dmg_url = array_to_base64_png(dmg_img)
    folium.raster_layers.ImageOverlay(
        image=dmg_url,
        bounds=[[sim.lat_min, sim.lon_min], [sim.lat_max, sim.lon_max]],
        opacity=0.8,
        name="Damage Intensity Overlay"
    ).add_to(m)

# Ash overlay
if show_ash:
    ash_img = sim.compute_ash_overlay(
        radius * ash_scale,
        wind_dir,
        wind_speed,
        max_radius=max_radius_km,
        cmap_name="Greys"
    )
    ash_url = array_to_base64_png(ash_img)
    folium.raster_layers.ImageOverlay(
        image=ash_url,
        bounds=[[sim.lat_min, sim.lon_min], [sim.lat_max, sim.lon_max]],
        opacity=0.8,
        name="Ash Plume Overlay"
    ).add_to(m)

# Impact rings
if show_rings and max_radius_km > 0:
    for r in range(5000, max_radius_km * 1000 + 1, 5000):
        folium.Circle(
            location=[v["lat"], v["lng"]],
            radius=r,
            color="purple",
            fill=False,
            dash_array="5,5",
            opacity=0.5
        ).add_to(m)

# Add Layer Control UI (top right)
folium.LayerControl().add_to(m)

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
m.add_child(FloatLegend(legend_damage_html))

# Colorbar (Right side)
def make_colorbar(cmap_name="violet_yellow", vmin=0, vmax=1, label="Damage Intensity"):
    fig, ax = plt.subplots(figsize=(0.4, 3))
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    from volcano_models import VolcanoSimulation
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






