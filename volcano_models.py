import numpy as np
import math
import matplotlib
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
        self.volcano_x = float(volcano_x)
        self.volcano_y = float(volcano_y)
        self.grid_res = int(grid_res)
        self.extent_km = float(extent_km)

        # Compute lat/lon span from km
        lat_deg_span = extent_km / 111.0
        lat_rad = math.radians(self.volcano_y)
        cos_lat = math.cos(lat_rad)
        self._lon_km_per_deg = 111.320 * cos_lat if abs(cos_lat) > 1e-6 else 111.320

        # Bounds in lat/lon
        lon_deg_span = extent_km / self._lon_km_per_deg
        self.lon_min = self.volcano_x - lon_deg_span
        self.lon_max = self.volcano_x + lon_deg_span
        self.lat_min = self.volcano_y - lat_deg_span
        self.lat_max = self.volcano_y + lat_deg_span

        # Grid
        xs = np.linspace(self.lon_min, self.lon_max, self.grid_res)
        ys = np.linspace(self.lat_min, self.lat_max, self.grid_res)
        self.XX, self.YY = np.meshgrid(xs, ys)

        # Local km offsets from volcano center
        self._dlon_km = (self.XX - self.volcano_x) * self._lon_km_per_deg
        self._dlat_km = (self.YY - self.volcano_y) * 111.0

        # Distance grid in km
        self.dist_grid = np.sqrt(self._dlon_km ** 2 + self._dlat_km ** 2)

    @staticmethod
    def get_colormap(cmap_name="inferno"):
        """Return a matplotlib colormap by name, including custom ones."""
        if cmap_name == "violet_yellow":
            return LinearSegmentedColormap.from_list(
                "violet_yellow", ["#800080", "#ff0000", "#ffa500", "#ffff00"]
            )
        elif cmap_name == "white_gray_black":
            return LinearSegmentedColormap.from_list(
                "white_gray_black", ["#ffffff", "#888888", "#000000"]
            )
        else:
            # Use the non-deprecated API (matplotlib >= 3.7)
            try:
                return matplotlib.colormaps[cmap_name]
            except (KeyError, AttributeError):
                return cm.get_cmap(cmap_name)  # fallback for older matplotlib

    def _array_to_rgba(self, array, cmap_name="inferno"):
        """Normalize array and convert to RGBA uint8, alpha tied to intensity."""
        cmap = VolcanoSimulation.get_colormap(cmap_name)
        minv = np.min(array)
        maxv = np.max(array)
        normed = (array - minv) / (maxv - minv + 1e-12)
        rgba = (cmap(normed) * 255).astype(np.uint8)
        rgba[..., 3] = (np.clip(normed * 1.5, 0, 1) * 255).astype(np.uint8)
        return rgba

    def compute_damage_overlay(
        self,
        radius,
        scale,
        eq_mag_num,
        max_radius,
        cmap_name="violet_yellow"
    ):
        """
        Compute a damage intensity overlay.

        Parameters
        ----------
        radius      : float  – inner reference radius in km
        scale       : int    – alert level 0–4
        eq_mag_num  : float  – earthquake magnitude 0–9 (exposed to UI now)
        max_radius  : float  – hard cutoff in km
        cmap_name   : str    – colormap name
        """
        if radius <= 0 or max_radius <= 0:
            return np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)

        scale_factor = np.clip(scale / 4.0, 0.0, 1.0)
        quake_factor = np.clip(eq_mag_num / 9.0, 0.0, 1.0)  # scale to Richter max ~9

        # Inverse-square attenuation (more physical than linear)
        with np.errstate(divide="ignore", invalid="ignore"):
            inv_sq = 1.0 / (1.0 + (self.dist_grid / max(radius, 1e-6)) ** 2)

        # Exponential falloff beyond the core radius
        falloff_km = max(1.0, max_radius / 5.0)
        damage = inv_sq * np.exp(-self.dist_grid / falloff_km)
        damage *= scale_factor * quake_factor

        # Hard cutoff at max_radius
        damage[self.dist_grid > max_radius] = 0.0
        damage = np.clip(damage / (damage.max() + 1e-12), 0.0, 1.0)

        return self._array_to_rgba(damage, cmap_name)

    def compute_ash_overlay(
        self,
        radius,
        wind_dir,
        wind_speed,
        max_radius,
        cmap_name="white_gray_black"
    ):
        """
        Compute an ash-plume overlay using an elongated Gaussian with
        wind-driven elongation and mild turbulence noise.

        Parameters
        ----------
        radius      : float  – plume base radius in km
        wind_dir    : float  – meteorological wind direction in degrees
                               (direction wind is coming FROM; plume goes opposite)
        wind_speed  : float  – wind speed in km/h
        max_radius  : float  – hard cutoff in km
        cmap_name   : str    – colormap name
        """
        if radius <= 0 or max_radius <= 0:
            return np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)

        # Plume travels downwind (opposite of "from" direction)
        ash_angle_deg = (wind_dir + 180.0) % 360.0
        ash_rad = math.radians(ash_angle_deg)
        ux, uy = math.sin(ash_rad), math.cos(ash_rad)  # unit vector downwind

        # Project grid into plume-aligned coordinates
        parallel = self._dlon_km * ux + self._dlat_km * uy   # along plume axis
        perp     = -self._dlon_km * uy + self._dlat_km * ux  # across plume

        wind_factor = max(0.1, wind_speed / 10.0)

        # Stronger wind → narrower, longer plume
        parallel_sigma = max(1.0, (radius + 1.0) * 0.5 * wind_factor)
        perp_sigma     = max(0.5, (radius + 1.0) * 0.2 / max(0.5, wind_factor ** 0.3))

        # Core Gaussian plume
        gauss = np.exp(
            -0.5 * ((parallel / parallel_sigma) ** 2 + (perp / perp_sigma) ** 2)
        )

        # Sigmoid to sharpen the downwind bias (suppress upwind)
        bias = 1.0 / (1.0 + np.exp(-1.2 * parallel / max(parallel_sigma * 0.6, 1e-6)))
        gauss *= bias

        # Mild turbulence: low-frequency noise scaled by distance from center
        rng = np.random.default_rng(seed=42)  # deterministic seed → stable renders
        noise = rng.uniform(0.88, 1.12, size=gauss.shape)
        turb_weight = np.clip(self.dist_grid / max(max_radius, 1e-6), 0, 1) * 0.15
        gauss *= (1.0 - turb_weight + turb_weight * noise)

        # Radial attenuation
        radial_atten = np.exp(-self.dist_grid / max(1.0, max_radius / 2.5))
        ash = gauss * radial_atten

        # Normalise and scale by plume intensity relative to max_radius
        max_ash = np.max(ash)
        ash = ash / max_ash if max_ash > 0 else ash
        intensity = np.clip((radius / max(1.0, max_radius)) * 1.3 + 0.05, 0.0, 1.0)
        ash *= intensity

        # Hard cutoff (plume can bleed slightly beyond max_radius)
        ash[self.dist_grid > max_radius * 1.6] = 0.0
        ash = np.clip(ash * 2.0, 0.0, 1.0)

        return self._array_to_rgba(ash, cmap_name)
