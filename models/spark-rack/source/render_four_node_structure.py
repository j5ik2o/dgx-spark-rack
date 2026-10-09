# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib==3.10.7", "numpy==2.3.3"]
# ///
"""CADの面分割データから組立図を描く。既存画像の加工は行わない。"""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np


def render(path):
    scene = json.loads(path.read_text())
    right = np.array([1, 1, 0], dtype=float) / np.sqrt(2)
    up = np.array([-1, 1, 2], dtype=float) / np.sqrt(6)
    eye = np.array([1, -1, 1], dtype=float) / np.sqrt(3)
    light = np.array([0.1, -0.5, 1.0]); light /= np.linalg.norm(light)
    faces, colors, depths = [], [], []
    for item in scene:
        vertices = np.asarray(item['vertices'])
        triangles = vertices[np.asarray(item['faces'], dtype=int)]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        normals /= np.maximum(lengths[:, None], 1e-12)
        shade = 0.55 + 0.45 * np.maximum(0, normals @ light)
        rgb = np.asarray(item['color'])[None, :] * shade[:, None]
        rgba = np.column_stack([rgb, np.full(len(rgb), item['alpha'])])
        faces.append(np.stack([triangles @ right, triangles @ up], axis=-1))
        colors.append(rgba)
        depths.append(np.mean(triangles @ eye, axis=1))
    faces, colors, depths = np.concatenate(faces), np.concatenate(colors), np.concatenate(depths)
    order = np.argsort(depths, kind='stable')
    fig, ax = plt.subplots(figsize=(12.8, 9.6), dpi=125)
    ax.add_collection(PolyCollection(faces[order], facecolors=colors[order], edgecolors='none', antialiased=False))
    points = faces.reshape(-1, 2)
    low, high = points.min(axis=0), points.max(axis=0)
    margin = (high - low) * 0.08
    ax.set_xlim(low[0] - margin[0], high[0] + margin[0])
    ax.set_ylim(low[1] - margin[1], high[1] + margin[1])
    ax.set_aspect('equal'); ax.axis('off')
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(path.with_name(path.stem.removesuffix('-scene') + '.png'), facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    for path in sorted(Path(sys.argv[1]).glob('*-scene.json')):
        render(path)
