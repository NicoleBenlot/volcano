import numpy as np
import math
import matplotlib
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap


class VolcanoSimulation:
    """
    Geographic-aware simulation grid.
    - Grid is constructed in lat/lon around the volcano center using an extent in km.
    - Distance grid is computed in km using local lat/lon scaling.
    - Overlays return RGBA uint8 arrays; alpha is tied to intensity for proper blending.
    """

    def __init__(self, volcano_x=0.0, volcano_y=0.0, grid_res=240, extent_km=60.0):
        self.volcano_x = float(volcano_x)
        self.volcano_y = float(volcano_y)
        self.grid_res  = int(grid_res)
        self.extent_km = float(extent_km)

        # km-per-degree factors
        lat_rad = math.radians(self.volcano_y)
        cos_lat = math.cos(lat_rad)
        self._lon_km_per_deg = 111.320 * (cos_lat if abs(cos_lat) > 1e-6 else 1.0)
        self._lat_km_per_deg = 111.0

        # Lat/lon bounds
        lat_deg_span = extent_km / self._lat_km_per_deg
        lon_deg_span = extent_km / self._lon_km_per_deg
        self.lon_min = self.volcano_x - lon_deg_span
        self.lon_max = self.volcano_x + lon_deg_span
        self.lat_min = self.volcano_y - lat_deg_span
        self.lat_max = self.volcano_y + lat_deg_span

        # Grid in lon/lat
        xs = np.linspace(self.lon_min, self.lon_max, self.grid_res)
        ys = np.linspace(self.lat_min, self.lat_max, self.grid_res)
        self.XX, self.YY = np.meshgrid(xs, ys)

        # Local km offsets from volcano centre
        self._dlon_km = (self.XX - self.volcano_x) * self._lon_km_per_deg
        self._dlat_km = (self.YY - self.volcano_y) * self._lat_km_per_deg

        # Euclidean distance grid in km
        self.dist_grid = np.sqrt(self._dlon_km ** 2 + self._dlat_km ** 2)

        # Area of one grid cell in km²
        cell_lon_km = (self.lon_max - self.lon_min) / self.grid_res * self._lon_km_per_deg
        cell_lat_km = (self.lat_max - self.lat_min) / self.grid_res * self._lat_km_per_deg
        self._cell_area_km2 = cell_lon_km * cell_lat_km

    # ------------------------------------------------------------------
    # Colormap helpers
    # ------------------------------------------------------------------
    @staticmethod
    def get_colormap(cmap_name="inferno"):
        """Return a matplotlib colormap, including custom named ones."""
        if cmap_name == "violet_yellow":
            return LinearSegmentedColormap.from_list(
                "violet_yellow", ["#800080", "#ff0000", "#ffa500", "#ffff00"]
            )
        if cmap_name == "white_gray_black":
            return LinearSegmentedColormap.from_list(
                "white_gray_black", ["#ffffff", "#888888", "#000000"]
            )
        if cmap_name == "ash_orange":
            return LinearSegmentedColormap.from_list(
                "ash_orange", [
                    (0.00, "#1a0500"),
                    (0.25, "#7f1900"),
                    (0.50, "#e04000"),
                    (0.75, "#ff8c00"),
                    (1.00, "#ffe680"),
                ]
            )
        if cmap_name == "ash_yellow":
            # Transparent dark core → olive → bright yellow → white edge
            # Highly visible on satellite imagery; reads as "sulphur/gas cloud"
            return LinearSegmentedColormap.from_list(
                "ash_yellow", [
                    (0.00, "#0d0d00"),   # near-black core
                    (0.20, "#3d3d00"),   # dark olive
                    (0.45, "#999900"),   # olive-yellow
                    (0.70, "#cccc00"),   # bright yellow
                    (0.85, "#ffff33"),   # vivid yellow
                    (1.00, "#ffffcc"),   # pale cream edge
                ]
            )
        # Standard matplotlib colormaps (non-deprecated API)
        try:
            return matplotlib.colormaps[cmap_name]
        except (KeyError, AttributeError):
            return cm.get_cmap(cmap_name)

    def _array_to_rgba(self, array, cmap_name="inferno"):
        """Normalize *array* to [0,1], map through colormap, return RGBA uint8."""
        cmap   = VolcanoSimulation.get_colormap(cmap_name)
        vmin, vmax = array.min(), array.max()
        normed = (array - vmin) / (vmax - vmin + 1e-12)
        rgba   = (cmap(normed) * 255).astype(np.uint8)
        rgba[..., 3] = (np.clip(normed * 1.5, 0.0, 1.0) * 255).astype(np.uint8)
        return rgba

    # ------------------------------------------------------------------
    # Affected area helper
    # ------------------------------------------------------------------
    def compute_affected_area_km2(self, field, threshold=0.1):
        """
        Return the area (km²) where *field* exceeds *threshold*.
        field  : 2-D float array normalised to [0, 1]
        """
        return float(np.sum(field > threshold) * self._cell_area_km2)

    # ------------------------------------------------------------------
    # Damage overlay
    # ------------------------------------------------------------------
    def compute_damage_overlay(
        self,
        radius,
        scale,
        eq_mag_num,
        max_radius,
        cmap_name="violet_yellow",
    ):
        """
        Damage intensity field (inverse-square + exponential falloff).
        Returns (rgba_array, normalised_field).
        """
        if radius <= 0 or max_radius <= 0:
            empty = np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)
            return empty, np.zeros(self.dist_grid.shape)

        scale_factor = float(np.clip(scale      / 4.0, 0.0, 1.0))
        quake_factor = float(np.clip(eq_mag_num / 9.0, 0.0, 1.0))

        inv_sq = 1.0 / (1.0 + (self.dist_grid / max(radius, 1e-6)) ** 2)
        falloff_km = max(1.0, max_radius / 5.0)
        damage = inv_sq * np.exp(-self.dist_grid / falloff_km)
        damage *= scale_factor * quake_factor
        damage[self.dist_grid > max_radius] = 0.0
        peak = damage.max()
        if peak > 1e-12:
            damage /= peak

        return self._array_to_rgba(damage, cmap_name), damage

    # ------------------------------------------------------------------
    # Ash-plume overlay
    # ------------------------------------------------------------------
    def compute_ash_overlay(
        self,
        radius,
        wind_dir,
        wind_speed,
        max_radius,
        cmap_name="ash_orange",
    ):
        """
        Stable Gaussian ash-plume, well-behaved across 0–200 km/h.
        Returns (rgba_array, normalised_field).
        """
        if radius <= 0 or max_radius <= 0:
            empty = np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)
            return empty, np.zeros(self.dist_grid.shape)

        down_deg = (wind_dir + 180.0) % 360.0
        down_rad = math.radians(down_deg)
        ux = math.sin(down_rad)
        uy = math.cos(down_rad)

        par  =  self._dlon_km * ux + self._dlat_km * uy
        perp = -self._dlon_km * uy + self._dlat_km * ux

        wind_factor = math.log1p(max(0.0, wind_speed) / 10.0)
        base = max(1.0, radius)
        sigma_par  = max(1.5, base * (1.0 + wind_factor))
        sigma_perp = max(0.8, base / (1.0 + 0.3 * wind_factor))

        gauss = np.exp(
            -0.5 * ((par / sigma_par) ** 2 + (perp / sigma_perp) ** 2)
        )

        k    = 3.0 / max(sigma_par, 1e-6)
        bias = 1.0 / (1.0 + np.exp(-k * par))
        gauss *= bias

        decay_km = max(1.0, max_radius * 0.5)
        envelope = np.exp(-self.dist_grid / decay_km)
        ash = gauss * envelope

        rng   = np.random.default_rng(seed=42)
        noise = rng.uniform(0.90, 1.10, size=ash.shape)
        t_w   = np.clip(self.dist_grid / max(max_radius, 1e-6), 0.0, 1.0) * 0.12
        ash  *= (1.0 - t_w + t_w * noise)

        ash[self.dist_grid > max_radius * 1.5] = 0.0
        peak = ash.max()
        if peak > 1e-12:
            ash /= peak

        intensity = float(np.clip(radius / max(max_radius, 1e-6) * 1.4 + 0.1, 0.0, 1.0))
        ash = np.clip(ash * intensity, 0.0, 1.0)

        return self._array_to_rgba(ash, cmap_name), ash
