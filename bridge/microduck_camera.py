"""Render the existing duck's head camera only while a Camera757 receiver subscribes."""
import os
from pathlib import Path
import time

import numpy as np

from camera757 import Camera757Server


def install(body_server):
    original_run=body_server.run

    def run(world,headless):
        if os.environ.get('MICRODUCK_VIDEO','1')!='1':
            return original_run(world,headless)
        if any(body.camera is not None for body in world.bodies):
            raise RuntimeError('Do not combine DUCK_SIM_CAMERAS with MICRODUCK_VIDEO=1; use MICRODUCK_VIDEO=0 for upstream media')
        from mjlab_microduck.sim.camera import Camera
        path=Path(os.environ['MICRODUCK_HUD_FILE']).with_name('v7rc-video.json')
        server=Camera757Server(path)
        original_step=world.step
        world.model.vis.global_.offheight=max(640,world.model.vis.global_.offheight)
        camera=Camera(world.model,f'{world.bodies[0].prefix}head_camera',width=360,height=640)
        with world.lock:camera.renderer.update_scene(world.data,camera=camera.camera)
        camera.renderer.render()  # Warm shaders before a receiver starts controlling the duck.
        next_frame=0
        # Rotation is applied to pixels, not just packet metadata. A portrait render
        # corrects the onboard quarter-turn mount to an upright 640x360 output.
        def step(times=1):
            nonlocal camera,next_frame
            original_step(times)
            now=time.monotonic()
            if not server.wants_frame() or now<next_frame:return
            with world.lock:
                camera.renderer.update_scene(world.data,camera=camera.camera)
            rgb=np.ascontiguousarray(np.rot90(camera.renderer.render(),k=-1))
            server.publish(rgb)
            next_frame=time.monotonic()+.1  # Start at <=10 FPS to preserve the 50 Hz loop.
        world.step=step
        try:return original_run(world,headless)
        finally:
            server.close()
            if camera is not None:camera.renderer.close()
    body_server.run=run
