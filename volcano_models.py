import numpy as np
import math
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap

class VolcanoSimulation:
    def __init__(self, volcano_x=0, volcano_y=0, grid_res=240, bounds=(-60, 60, -60, 60)):
        self.volcano_x = volcano_x
        self.volcano_y = volcano_y
        self.x_min, self.x_max, self.y_min, self.y_max = bounds
        xs = np.linspace(self.x_min, self.x_max, grid_res)
        ys = np.linspace(self.y_min, self.y_max, grid_res)
        self.XX, self.YY = np.meshgrid(xs, ys)
        self.dist_grid = np.sqrt((self.XX - volcano_x) ** 2 + (self.YY - volcano_y) ** 2)

    # ✅ Centralized colormap helper
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
        normed = (array - np.min(array)) / (np.max(array) - np.min(array) + 1e-9)
        rgba_img = (cmap(normed) * 255).astype(np.uint8)
        return rgba_img

    def compute_damage_overlay(self, radius, scale, eq_mag_num, max_radius, cmap_name="violet_yellow"):
        if radius <= 0 or max_radius <= 0:
            return np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)

        base = np.clip(1 - (self.dist_grid / radius), 0, 1)
        scale_factor = scale / 4.0
        quake_factor = min(eq_mag_num / 7.0, 1.0)

        damage = base * scale_factor * quake_factor
        damage *= np.exp(-self.dist_grid / max(1.0, (max_radius / 6.0)))
        damage[self.dist_grid > max_radius] = 0.0

        # ✅ Boost contrast so center is vivid
        damage = np.clip(damage * 2.0, 0, 1)

        return self._array_to_rgba(damage, cmap_name)

    def compute_ash_overlay(self, radius, wind_dir, wind_speed, max_radius, cmap_name="white_gray_black"):
        if radius <= 0 or max_radius <= 0:
            return np.zeros((*self.dist_grid.shape, 4), dtype=np.uint8)

        ash_angle_deg = (wind_dir + 180) % 360
        ash_rad = np.deg2rad(ash_angle_deg)
        ux, uy = math.sin(ash_rad), math.cos(ash_rad)

        wind_factor = max(0.1, wind_speed / 10.0)
        parallel_sigma = max(1.0, (radius + 1.0) * 0.4 * wind_factor)
        perp_sigma = max(0.5, (radius + 1.0) * 0.25)

        RX, RY = self.XX - self.volcano_x, self.YY - self.volcano_y
        parallel = RX * ux + RY * uy
        perp = -RX * uy + RY * ux

        gauss = np.exp(-0.5 * ((parallel / parallel_sigma) ** 2 + (perp / perp_sigma) ** 2))
        gauss *= 1 / (1 + np.exp(-0.8 * parallel))

        radial_atten = np.exp(-self.dist_grid / max(1.0, max_radius / 3.0))
        ash = gauss * radial_atten
        ash /= np.max(ash) if np.max(ash) > 0 else 1
        ash *= np.clip((radius / max(1.0, max_radius)) * 1.2 + 0.05, 0, 1)
        ash[self.dist_grid > max_radius * 1.5] = 0

        # ✅ Boost contrast
        ash = np.clip(ash * 2.0, 0, 1)

        return self._array_to_rgba(ash, cmap_name)