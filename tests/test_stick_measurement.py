"""Independent geometry checks for measured, rather than requested, motion."""
import importlib.util
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stick_measurement',ROOT/'scripts/measure-stick-response.py')
measurement=importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)


def sample(x,y,yaw,sim_time,wall_time):
    return {'yaw':yaw,'elapsed':wall_time,'sensor':{'trunk':[x,y,.115],'sim_time':sim_time}}


class MotionGeometryTests(unittest.TestCase):
    def test_forward_when_facing_world_y_and_distinct_time_bases(self):
        # One metre along world Y while facing Y is forward, with no lateral motion.
        result=measurement.motion([sample(0,0,math.pi/2,0,0),sample(0,1,math.pi/2,2,4)])
        self.assertAlmostEqual(result['vx_m_s'],.5)
        self.assertAlmostEqual(result['vx_wall_m_s'],.25)
        self.assertAlmostEqual(result['vy_m_s'],0)
        self.assertAlmostEqual(result['realtime_factor'],.5)

    def test_signed_yaw_across_wrap_boundary(self):
        for degrees in [(179,-179,2),(-179,179,-2)]:
            with self.subTest(degrees=degrees):
                a,b,expected=degrees
                result=measurement.motion([sample(0,0,math.radians(a),0,0),sample(0,0,math.radians(b),1,1)])
                self.assertAlmostEqual(result['yaw_deg_s'],expected)


if __name__=='__main__':unittest.main()
