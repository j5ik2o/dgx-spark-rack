"""実際のマクロ形状を三角形化して確認画像を作る（FreeCAD同梱Pythonで実行）。"""
from pathlib import Path
import FreeCAD as App
import Part
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import proj3d
import numpy as np

ROOT = Path(__file__).resolve().parent
font_path = Path('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc')
if font_path.exists():
    font_manager.fontManager.addfont(str(font_path))
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font_path)).get_name()
n = {}
macro = ROOT / 'freecad_fan_controller.py'
exec(compile(macro.read_text(), str(macro), 'exec'), n)
import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path, help='今回のbuild出力フォルダ')
OUT = parser.parse_args().output.resolve() / 'preview'
OUT.mkdir(parents=True, exist_ok=False)


def draw(ax, shape, color, lift=0):
    if not hasattr(ax, '_cad_triangles'):
        ax._cad_triangles, ax._cad_colors = [], []
    light = np.array([-0.4, -0.5, 0.8])
    light /= np.linalg.norm(light)
    for face in shape.Faces:
        vertices, triangles = face.tessellate(0.10)
        points = np.array([[p.x, p.y, p.z] for p in vertices])
        for triangle in triangles:
            polygon = points[list(triangle)].copy()
            center = polygon.mean(axis=0)
            uv = face.Surface.parameter(App.Vector(*center))
            normal = face.normalAt(*uv)
            brightness = .72 + .28 * np.dot([normal.x, normal.y, normal.z], light)
            polygon[:, 2] += lift
            ax._cad_triangles.append(polygon)
            ax._cad_colors.append(np.array(to_rgb(color)) * brightness)


def finish(fig):
    # ピクセルごとの深度判定。細長い三角形は描画順だけでは正しく隠れない。
    fig.set_dpi(160)
    fig.canvas.draw()
    width, height = fig.canvas.get_width_height()
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    depth = np.full((height, width), np.inf)
    for ax in fig.axes:
        matrix = ax.get_proj()
        for triangle, color in zip(ax._cad_triangles, ax._cad_colors):
            px, py, pz = proj3d.proj_transform(*np.array(triangle).T, matrix)
            xy = ax.transData.transform(np.column_stack((px, py)))
            x0,y0 = np.maximum(np.floor(xy.min(axis=0)).astype(int),0)
            x1,y1 = np.minimum(np.ceil(xy.max(axis=0)).astype(int),[width-1,height-1])
            if x1 < x0 or y1 < y0:
                continue
            (a,b),(c,d),(e,f) = xy
            denom = (d-f)*(a-e)+(e-c)*(b-f)
            if abs(denom)<1e-10:
                continue
            xx,yy = np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
            u = ((d-f)*(xx-e)+(e-c)*(yy-f))/denom
            v = ((f-b)*(xx-e)+(a-e)*(yy-f))/denom
            w = 1-u-v
            z = u*pz[0]+v*pz[1]+w*pz[2]
            region = depth[y0:y1+1,x0:x1+1]
            mask = (u>=-1e-8)&(v>=-1e-8)&(w>=-1e-8)&(z<region)
            region[mask] = z[mask]
            rgba[y0:y1+1,x0:x1+1][mask] = [*np.clip(np.array(color)*255,0,255).astype(np.uint8),255]
    fig.figimage(np.flipud(rgba), xo=0, yo=0, zorder=5)


def setup(ax, zmax=30, elev=35, azim=-115):
    ax.set_xlim(-9, 84)
    ax.set_ylim(-12, 38)
    ax.set_zlim(-9, zmax)
    ax.set_box_aspect((93, 50, zmax+9))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_facecolor('#f4f6f8')


fig = plt.figure(figsize=(14, 8), facecolor='#f4f6f8')
fig.suptitle('ファンコントローラーケース｜角丸の長方形', fontsize=20, y=.95)
ax = fig.add_subplot(121, projection='3d')
setup(ax, elev=36)
draw(ax, n['body_final'], '#52758d')
draw(ax, n['lid_final'], '#dce4eb')
ax.set_title('組立状態', fontsize=15)
ax = fig.add_subplot(122, projection='3d')
setup(ax, zmax=61, elev=32)
draw(ax, n['body_final'], '#52758d')
draw(ax, n['lid_final'], '#dce4eb', lift=35)
ax.set_title('本体と蓋を離した状態', fontsize=15)
fig.text(.05,.12,'青：本体　　灰：蓋　／　四隅 R3mm・ねじ固定部は側壁内に配置・外側の突起なし', fontsize=12)
fig.text(.05,.07,'配線出口は仮寸法を含みます。部品・ねじ・ケーブルは非表示。実物適合は未確認です。', fontsize=11, color='#88521b')
fig.subplots_adjust(left=.02,right=.98,bottom=.18,top=.83,wspace=.02)
finish(fig)
fig.savefig(OUT/'assembly.png', dpi=160, facecolor=fig.get_facecolor())
plt.close(fig)

fig = plt.figure(figsize=(14, 8), facecolor='#f4f6f8')
fig.suptitle('内部と開口位置の確認', fontsize=20, y=.95)
ax = fig.add_subplot(121, projection='3d')
setup(ax, elev=62, azim=-105)
draw(ax, n['body_final'], '#52758d')
ax.set_title('本体内部：受けリブ・底面スリット', fontsize=14)
ax = fig.add_subplot(122, projection='3d')
setup(ax, elev=90, azim=-90)
draw(ax, n['lid_final'], '#b9cbd8')
ax.set_title('蓋の上面：表示窓・つまみ穴', fontsize=14)
fig.text(.05,.12,'表示窓 32.73 × 10.93 mm　／　つまみ穴 Ø8 mm　／　端子台の突出は内部の空間で吸収',fontsize=12)
fig.text(.05,.07,'画像はマクロのソリッドから生成。上面図の左右は基板の左右と一致します。',fontsize=11,color='#52606d')
fig.subplots_adjust(left=.02,right=.98,bottom=.18,top=.83,wspace=.02)
finish(fig)
fig.savefig(OUT/'details.png',dpi=160,facecolor=fig.get_facecolor())
plt.close(fig)
App.closeDocument(n['doc'].Name)
print(OUT)
