"""FreeCAD専用プロセス。Qt終了時の問題を親タスクから分離する。"""
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
MODULES = {
    'spark-rack': 'build_spark_rack',
    'adapter-rack': 'build_adapter_rack',
    'fan-controller': 'build_fan_controller',
}


def main():
    import FreeCAD as App
    import FreeCADGui as Gui
    model, result_file = sys.argv[1:]
    Gui.showMainWindow()
    sys.path.insert(0, str(ROOT / 'models' / model / 'source'))
    output = importlib.import_module(MODULES[model]).build()
    Path(result_file).write_text(json.dumps({'output': str(output)}))
    for name in list(App.listDocuments()):
        App.closeDocument(name)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
