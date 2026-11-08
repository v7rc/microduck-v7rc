"""Stream the head camera from a private MuJoCo model and render thread."""
from copy import copy
import os
from pathlib import Path
import threading
import time
from typing import Callable

import mujoco
import numpy as np
from PIL import Image

from camera757 import Camera757Server

_STATE = mujoco.mjtState.mjSTATE_INTEGRATION
_FPS = 30
_RENDER_WIDTH = 270
_RENDER_HEIGHT = 480
_OUTPUT_SIZE = (640, 360)
_SHADOW = int(mujoco.mjtRndFlag.mjRND_SHADOW)
_REFLECTION = int(mujoco.mjtRndFlag.mjRND_REFLECTION)


def stream(world, model, camera, server, stop):
    data = mujoco.MjData(model)
    state = np.empty(mujoco.mj_stateSize(model, _STATE))
    last_sim_time = None
    period = 1 / _FPS
    deadline = time.monotonic()

    while not stop.is_set() and not server.stopped.is_set():
        if server.wants_frame():
            if not world.lock.acquire(blocking=False):
                stop.wait(0.001)
                continue
            try:
                current_sim_time = world.data.time
                fresh = current_sim_time != last_sim_time
                if fresh:
                    mujoco.mj_getState(world.model, world.data, state, _STATE)
            finally:
                world.lock.release()
            if not fresh:
                stop.wait(0.001)
                continue
            last_sim_time = current_sim_time
            mujoco.mj_setState(model, data, state, _STATE)
            mujoco.mj_fwdPosition(model, data)
            camera.renderer.update_scene(data, camera=camera.camera)
            camera.renderer.scene.flags[_SHADOW] = False
            camera.renderer.scene.flags[_REFLECTION] = False
            # The simulated sensor is mounted a quarter turn off.
            upright = Image.fromarray(np.rot90(camera.renderer.render(), k=-1))
            rgb = np.asarray(upright.resize(_OUTPUT_SIZE, Image.Resampling.BILINEAR))
            server.publish(rgb)

        # Keep the cadence across small overruns, without accumulating old slots.
        deadline += period
        now = time.monotonic()
        if deadline < now - period:
            deadline = now
        stop.wait(max(0, deadline - time.monotonic()))


def install(body_server):
    original_run = body_server.run

    def run(world, headless):
        if os.environ.get('MICRODUCK_VIDEO', '1') != '1':
            return original_run(world, headless)
        if any(body.camera is not None for body in world.bodies):
            raise RuntimeError('Do not combine DUCK_SIM_CAMERAS with MICRODUCK_VIDEO=1; use MICRODUCK_VIDEO=0 for upstream media')

        from mjlab_microduck.sim.camera import Camera
        from mujoco.rendering.classic import gl_context

        model = copy(world.model)
        model.vis.global_.offwidth = _RENDER_WIDTH
        model.vis.global_.offheight = _RENDER_HEIGHT
        model.vis.quality.offsamples = 0
        name = f'{world.bodies[0].prefix}head_camera'
        path = Path(os.environ['MICRODUCK_HUD_FILE']).with_name('v7rc-video.json')
        stop = threading.Event()
        camera = None
        detach_context: Callable[[], None] | None = None

        try:
            # GLFW window creation and destruction must stay on the main thread.
            # Its detached context can be current on the render thread in between.
            if getattr(gl_context.GLContext, '__module__', None) == 'mujoco.glfw':
                import glfw

                def detach_context():
                    glfw.make_context_current(None)

                camera = Camera(model, name, width=_RENDER_WIDTH, height=_RENDER_HEIGHT)
                detach_context()

            server = Camera757Server(path)

            def render():
                active_camera = camera
                try:
                    if active_camera is None:
                        active_camera = Camera(model, name, width=_RENDER_WIDTH, height=_RENDER_HEIGHT)
                    stream(world, model, active_camera, server, stop)
                except (Exception, SystemExit) as error:
                    print(f'== V7RC camera render error: {error}', flush=True)
                    server.close()
                finally:
                    if detach_context is not None:
                        detach_context()
                    elif active_camera is not None:
                        active_camera.renderer.close()

            worker = threading.Thread(target=render, name='v7rc-camera-render', daemon=True)
            try:
                worker.start()
                return original_run(world, headless)
            finally:
                stop.set()
                if worker.ident is not None:
                    worker.join()
                server.close()
        finally:
            if camera is not None:
                camera.renderer.close()

    body_server.run = run
