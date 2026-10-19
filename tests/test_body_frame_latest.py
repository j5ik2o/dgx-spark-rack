"""失敗した生成を公開せず、既存データを保存して案内だけを更新する。"""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'models/spark-rack/source'))
from build_body_frame import publish_latest


class LatestPreviewTests(unittest.TestCase):
    def make_run(self,parent,name,status='generated'):
        folder=parent/name
        folder.mkdir()
        (folder/'manifest.json').write_text(json.dumps(dict(status=status)),encoding='utf-8')
        (folder/'body-frame.html').write_text('<html>生成済みモデル</html>',encoding='utf-8')
        return folder

    def test_publishing_a_new_run_preserves_previous_generated_files(self):
        with tempfile.TemporaryDirectory() as temp:
            parent=Path(temp)
            first=self.make_run(parent,'first')
            second=self.make_run(parent,'second')
            publish_latest(first)
            publish_latest(second)
            self.assertEqual((parent/'latest').resolve(),second.resolve())
            self.assertTrue((first/'body-frame.html').exists())
            self.assertEqual(list(parent.glob('.latest-*')),[])

    def test_a_failed_run_does_not_replace_the_previous_preview(self):
        with tempfile.TemporaryDirectory() as temp:
            parent=Path(temp)
            first=self.make_run(parent,'first')
            failed=self.make_run(parent,'failed','failed')
            publish_latest(first)
            with self.assertRaisesRegex(ValueError,'完了していない'):
                publish_latest(failed)
            self.assertEqual((parent/'latest').resolve(),first.resolve())

    def test_real_directories_are_never_replaced_by_the_latest_link(self):
        with tempfile.TemporaryDirectory() as temp:
            parent=Path(temp)
            run=self.make_run(parent,'run')
            (parent/'latest').mkdir()
            (parent/'latest'/'keep.txt').write_text('preserve',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'既存'):
                publish_latest(run)
            self.assertEqual((parent/'latest'/'keep.txt').read_text(encoding='utf-8'),'preserve')
