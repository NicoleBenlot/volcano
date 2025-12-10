import numpy as np
import math
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap

class VolcanoSimulation:
    """
    Geographic-aware simulation grid:
    - Grid is constructed in lat/lon around the volcano center using an extent in km.
    - Distance grid is computed in km using local lat/lon scaling.
    - Overlays return RGBA arrays with alpha channel driven by intensity for proper blending.
    """

    def __init__(self, volcano_x=0.0, volcano_y=0.0, grid_res=240, extent_km=60.0):
        # volcano_x = longitude, volcano_y = latitude
        self.volcano_x = float(volcano_x)
        self.volcano_y = float(volcano_y)
        self.grid_res = int(grid_res)
        self.extent_km = float(extent_km)

        # Compute lat/lon span from km
        lat_deg_span = extent_km / 111.0  # ~111 km per degree latitude
        lat_rad = math.radians(self.volcano_y)
        lon_km_per_deg = 111.320 * math.cos(lat_rad) if abs(math.cos(lat_rad)) > 1e-6 else 111.320
        lon_deg_span = extent_km / lon_km_per_deg

        # Bounds in lat/lon
        self.lon_min = self.volcano_x - lon_deg_span
        self.lon_max = self.volcano_x + lon_deg_span
        self.lat_min = self.volcano_y - lat_deg_span
        self.lat_max = self.volcano_y + lat_deg_span

        # Grid
        xs = np.linspace(self.lon_min, self.lon_max, self.grid_res)  # longitude
        ys = np.linspace(self.lat_min, self.lat_max, self.grid_res)  # latitude
        self.XX, self.YY = np.meshgrid(xs, ys)

        # Distance grid in km (local planar approximation)
        dlon = (self.XX - self.volcano_x) * lon_km_per_deg
        dlat = (self.YY - self.volcano_y) * 111.0
        self.dist_grid = np.sqrt(dlon ** 2 + dlat ** 2)

    @staticmethod
    def get_colormap(cmap_name="inferno"):
        if cmap_name == "violet_yellow":
            return LinearSegmentedColormap.from_list(
                "violet_yellow", ["#800080", "#ff0000", "#ffa500", "#ffff00"]
            )
        elif cmap_name == "white_gray_black":
            return LinearSegmentedColormap.from_list(
                "white_gray_black", ["#ffffff", "#888888", "#000000"]
            )
        else:
            return cm.get_cmap(cmap_name)

    def _array_to_rgba(self, array, cmap_name="inferno"):
        cmap = VolcanoSimulation.get_colormap(cmap_name)
        minv = np.min(array)
        maxv = np.max(array)
        normed = (array - minv) / (maxv - minv + 1e-12)
    
        rgba = (cmap(normed) * 255).astype(np.uint8)
        # 🔥 Boost alpha channel for visibility
        rgba[..., 3] = (np.clip(normed * 1.5, 0, 1) * 255).astype(np.uint8)
        return rgba

    def compute_damage_overlay(self, radius, scale, eq_mag_num, max_radius, cmap_name="violet_yellow"):
        """
        radius: km, scale: 0..4 alert level, eq_mag_num ~ 0..7
        max_radius: km cutoff
        """
        if radius <= 0 or max_radius <= 0:
            # Transparent image over the same grid
            empty = np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)
            return empty

        base = np.clip(1.0 - (self.dist_grid / max(radius, 1e-6)), 0.0, 1.0)
        scale_factor = np.clip(scale / 4.0, 0.0, 1.0)
        quake_factor = np.clip(eq_mag_num / 7.0, 0.0, 1.0)

        damage = base * scale_factor * quake_factor
        # Distance attenuation
        falloff_km = max(1.0, (max_radius / 6.0))
        damage *= np.exp(-self.dist_grid / falloff_km)
        # Hard cutoff
        damage[self.dist_grid > max_radius] = 0.0
        damage = np.clip(damage * 2.0, 0.0, 1.0)

        return self._array_to_rgba(damage, cmap_name)

    def compute_ash_overlay(self, radius, wind_dir, wind_speed, max_radius, cmap_name="white_gray_black"):
        """
        radius: km, wind_dir: degrees (meteorological, plume goes downwind),
        wind_speed: km/h, max_radius: km cutoff
        """
        if radius <= 0 or max_radius <= 0:
            empty = np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)
            return empty

        # Plume axis (downwind)
        ash_angle_deg = (wind_dir + 180) % 360
        ash_rad = math.radians(ash_angle_deg)
        ux, uy = math.sin(ash_rad), math.cos(ash_rad)

        # Local km coordinates relative to volcano
        # Use same dlon/dlat scale as in init
        lat_rad = math.radians(self.volcano_y)
        lon_km_per_deg = 111.320 * math.cos(lat_rad) if abs(math.cos(lat_rad)) > 1e-6 else 111.320
        RX_km = (self.XX - self.volcano_x) * lon_km_per_deg
        RY_km = (self.YY - self.volcano_y) * 111.0

        # Rotate into plume coordinates
        parallel = RX_km * ux + RY_km * uy
        perp = -RX_km * uy + RY_km * ux

        wind_factor = max(0.1, wind_speed / 10.0)
        parallel_sigma = max(1.0, (radius + 1.0) * 0.4 * wind_factor)
        perp_sigma = max(0.5, (radius + 1.0) * 0.25)

        gauss = np.exp(-0.5 * ((parallel / parallel_sigma) ** 2 + (perp / perp_sigma) ** 2))
        # Sharpen downwind bias
        gauss *= 1.0 / (1.0 + np.exp(-0.8 * parallel / max(parallel_sigma, 1e-6)))

        radial_atten = np.exp(-self.dist_grid / max(1.0, max_radius / 3.0))
        ash = gauss * radial_atten

        max_ash = np.max(ash)
        ash = ash / max_ash if max_ash > 0 else ash
        ash *= np.clip((radius / max(1.0, max_radius)) * 1.2 + 0.05, 0.0, 1.0)
        ash[self.dist_grid > max_radius * 1.5] = 0.0
        ash = np.clip(ash * 2.0, 0.0, 1.0)

        return self._array_to_rgba(ash, cmap_name)
