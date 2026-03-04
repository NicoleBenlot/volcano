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

    # ------------------------------------------------------------------
    # Colormap helpers
    # ------------------------------------------------------------------
    @staticmethod
    def get_colormap(cmap_name="inferno"):
        """Return a matplotlib colormap, including two custom named ones."""
        if cmap_name == "violet_yellow":
            return LinearSegmentedColormap.from_list(
                "violet_yellow", ["#800080", "#ff0000", "#ffa500", "#ffff00"]
            )
        if cmap_name == "white_gray_black":
            return LinearSegmentedColormap.from_list(
                "white_gray_black", ["#ffffff", "#888888", "#000000"]
            )
        # Non-deprecated path (matplotlib ≥ 3.7); fallback for older builds
        try:
            return matplotlib.colormaps[cmap_name]
        except (KeyError, AttributeError):
            return cm.get_cmap(cmap_name)

    def _array_to_rgba(self, array, cmap_name="inferno"):
        """Normalize *array* to [0,1], map through colormap, return RGBA uint8."""
        cmap  = VolcanoSimulation.get_colormap(cmap_name)
        vmin, vmax = array.min(), array.max()
        normed = (array - vmin) / (vmax - vmin + 1e-12)
        rgba = (cmap(normed) * 255).astype(np.uint8)
        # Alpha proportional to intensity (boosted slightly so faint edges show)
        rgba[..., 3] = (np.clip(normed * 1.5, 0.0, 1.0) * 255).astype(np.uint8)
        return rgba

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

        Parameters
        ----------
        radius     : float – inner reference radius in km
        scale      : int   – alert level 0–4
        eq_mag_num : float – earthquake magnitude 0–9
        max_radius : float – hard cutoff in km
        cmap_name  : str
        """
        if radius <= 0 or max_radius <= 0:
            return np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)

        scale_factor = float(np.clip(scale / 4.0,        0.0, 1.0))
        quake_factor = float(np.clip(eq_mag_num / 9.0,   0.0, 1.0))

        # Inverse-square core (physical ground-shaking analogue)
        inv_sq = 1.0 / (1.0 + (self.dist_grid / max(radius, 1e-6)) ** 2)

        # Exponential envelope beyond the core
        falloff_km = max(1.0, max_radius / 5.0)
        damage = inv_sq * np.exp(-self.dist_grid / falloff_km)
        damage *= scale_factor * quake_factor

        # Hard cutoff
        damage[self.dist_grid > max_radius] = 0.0

        # Normalise to [0, 1]
        peak = damage.max()
        if peak > 1e-12:
            damage /= peak

        return self._array_to_rgba(damage, cmap_name)

    # ------------------------------------------------------------------
    # Ash-plume overlay  (completely rewritten for stability)
    # ------------------------------------------------------------------
    def compute_ash_overlay(
        self,
        radius,
        wind_dir,
        wind_speed,
        max_radius,
        cmap_name="white_gray_black",
    ):
        """
        Stable Gaussian ash-plume that remains well-behaved across the full
        wind-speed range (0 – 200 km/h).

        Model
        -----
        * The plume axis points downwind (wind_dir + 180°).
        * Along-axis sigma scales *sub-linearly* with wind speed so it never
          blows up:  sigma_par = base_spread * (1 + log1p(wind_factor))
        * Cross-axis sigma shrinks gently with wind:
          sigma_perp = base_spread / (1 + 0.25 * wind_factor)
        * A smooth sigmoid mask zeroes out the upwind half.
        * Mild deterministic turbulence (seeded) adds natural edge variation.
        * Everything is normalised at the end so intensity is consistent.

        Parameters
        ----------
        radius     : float – plume base radius in km (scaled by ash_scale in UI)
        wind_dir   : float – meteorological FROM-direction in degrees
        wind_speed : float – wind speed in km/h
        max_radius : float – hard cutoff in km
        cmap_name  : str
        """
        if radius <= 0 or max_radius <= 0:
            return np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)

        # ---- plume axis unit vector (downwind) -------------------------
        down_deg = (wind_dir + 180.0) % 360.0
        down_rad = math.radians(down_deg)
        ux = math.sin(down_rad)   # eastward component
        uy = math.cos(down_rad)   # northward component

        # ---- project grid onto plume-aligned axes ----------------------
        par  =  self._dlon_km * ux + self._dlat_km * uy   # along plume (+ = downwind)
        perp = -self._dlon_km * uy + self._dlat_km * ux   # across plume

        # ---- wind factor: logarithmic so high speeds don't explode -----
        # wind_speed = 0  → wind_factor = 0
        # wind_speed = 10 → wind_factor ≈ 1   (reference)
        # wind_speed = 50 → wind_factor ≈ 2.0
        # wind_speed = 200→ wind_factor ≈ 3.0
        wind_factor = math.log1p(max(0.0, wind_speed) / 10.0)

        # ---- sigma values (clamped to sensible minimum) ----------------
        base = max(1.0, radius)          # km; never let base collapse to zero

        # Along-axis: grows sub-linearly with wind (no blowup)
        sigma_par  = max(1.5, base * (1.0 + wind_factor))

        # Cross-axis: gently narrows in strong wind (plume gets focused)
        sigma_perp = max(0.8, base / (1.0 + 0.3 * wind_factor))

        # ---- core Gaussian ---------------------------------------------
        gauss = np.exp(
            -0.5 * (
                (par  / sigma_par ) ** 2 +
                (perp / sigma_perp) ** 2
            )
        )

        # ---- upwind suppression via smooth sigmoid ---------------------
        # Transitions from ~0 (upwind) to ~1 (downwind) over ~sigma_par
        k     = 3.0 / max(sigma_par, 1e-6)          # steepness
        bias  = 1.0 / (1.0 + np.exp(-k * par))      # sigmoid
        gauss = gauss * bias

        # ---- distance envelope (radial attenuation) --------------------
        # Decay over half of max_radius so plume fades before hard cutoff
        decay_km = max(1.0, max_radius * 0.5)
        envelope = np.exp(-self.dist_grid / decay_km)
        ash = gauss * envelope

        # ---- mild deterministic turbulence at plume edges --------------
        rng  = np.random.default_rng(seed=42)        # fixed seed → stable renders
        noise = rng.uniform(0.90, 1.10, size=ash.shape)
        # Turbulence weight grows toward the plume boundary
        t_weight = np.clip(self.dist_grid / max(max_radius, 1e-6), 0.0, 1.0) * 0.12
        ash = ash * (1.0 - t_weight + t_weight * noise)

        # ---- hard spatial cutoff (allow slight bleed past max_radius) --
        ash[self.dist_grid > max_radius * 1.5] = 0.0

        # ---- normalise & apply intensity scalar ------------------------
        peak = ash.max()
        if peak > 1e-12:
            ash /= peak

        # Intensity: how much ash is produced (scales with alert radius)
        intensity = float(np.clip(radius / max(max_radius, 1e-6) * 1.4 + 0.1, 0.0, 1.0))
        ash = np.clip(ash * intensity, 0.0, 1.0)

        return self._array_to_rgba(ash, cmap_name)
