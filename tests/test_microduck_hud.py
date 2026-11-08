import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bridge'))
from microduck_hud import HudViewer, snapshot, sticks, camera_snapshot
from v7rc_udp import Config, InputState


class HudTests(unittest.TestCase):
    def test_stopped_stopwatch_is_drawn_with_milliseconds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'stopwatch.json').write_text(json.dumps({'elapsed_ns': 127_045_000_000, 'started_ns': None}))
            viewer = Mock()
            viewer.viewport = Mock(width=640, height=480, left=0, bottom=0)
            hud = HudViewer(viewer, root / 'v7rc-input.json')
            hud.next_ip = float('inf')
            hud.logged_viewport = True
            hud.sync()
            right = viewer.set_texts.call_args.args[0][1][2]
            self.assertIn('TIME  02:07.045', right)

    def test_camera_on_requires_live_subscription_and_publisher(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'video.json'
            self.assertEqual(camera_snapshot(path,10)['status'],'CAMERA OFF')
            path.write_text(json.dumps({'published_monotonic':10,'active':True,'frames':42,'tx_fps':8,'peer':['172.20.10.1',50000]}))
            self.assertEqual(camera_snapshot(path,10),{'status':'CAMERA ON','frames':42,'fps':8,'peer':'172.20.10.1'})
            self.assertEqual(camera_snapshot(path,12),{'status':'CAMERA OFF','frames':42,'fps':0,'peer':'-'})
            path.write_text(json.dumps({'published_monotonic':12,'active':False,'frames':42,'tx_fps':8,'peer':['172.20.10.1',50000]}))
            self.assertEqual(camera_snapshot(path,12),{'status':'CAMERA OFF','frames':42,'fps':0,'peer':'-'})

    def test_stick_axis_layout_is_raw_not_control_direction(self):
        self.assertEqual(sticks([2000,1000,2000,1000]),((1,-1),(-1,1)))
        self.assertEqual(sticks([1500]*4),((0,0),(0,0)))

    def test_hud_distinguishes_expiry_and_stopped_publisher(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'input.json'
            value={'published_monotonic':10,'last_received_monotonic':9.9,
                   'channels':[1000,1500,1500,2000],'fps':33,'armed':True,'timeout_s':.3}
            path.write_text(json.dumps(value))
            self.assertEqual(snapshot(path,10)['status'],'LIVE')
            self.assertEqual(snapshot(path,10.3)['status'],'INPUT EXPIRED')
            stopped=snapshot(path,11)
            self.assertFalse(stopped['active'])
            self.assertEqual(stopped['fps'],0)
            self.assertEqual(stopped['channels'],value['channels'])
            path.write_text('{')
            self.assertEqual(snapshot(path,11)['status'],'WAITING FOR INPUT')

    def test_valid_unarmed_frames_count_as_receive_fps_but_invalid_do_not(self):
        state=InputState(Config())
        self.assertFalse(state.accept(b'SRT2000150015001500#','phone',1))
        self.assertEqual(state.received_total,1)
        self.assertEqual(state.last_received_channels,(2000,1500,1500,1500))
        state.accept(b'bad','phone',1.1)
        self.assertEqual(state.received_total,1)
        self.assertFalse(state.armed)


if __name__=='__main__':unittest.main()
