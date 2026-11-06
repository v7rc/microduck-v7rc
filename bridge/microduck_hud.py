"""Local body-server entry point adding a read-only V7RC HUD to MuJoCo."""
import json
import math
import os
from platform_support import advertised_ip
from pathlib import Path
import time

import mujoco
import mujoco.viewer
import numpy as np


def snapshot(path, now=None):
    now = time.monotonic() if now is None else now
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        data = {}
    published = data.get("published_monotonic", -math.inf)
    received = data.get("last_received_monotonic")
    alive = 0 <= now - published < 0.6
    fresh = alive and received is not None and 0 <= now - received < data.get("timeout_s", .3)
    channels = data.get("channels", [1500] * 4)
    if len(channels) != 4:
        channels = [1500] * 4
    return {**data, "channels": channels, "fps": data.get("fps", 0) if alive else 0,
            "status": ("LIVE" if data.get("armed") else "CENTER TO ARM") if fresh
                      else ("INPUT EXPIRED" if alive and received is not None else "WAITING FOR INPUT"),
            "active": fresh and data.get("armed", False), "fresh": fresh}


def sticks(channels, low=1000, center=1500, high=2000):
    # APP stick layout: left horizontal CH1, vertical CH2; right horizontal CH4,
    # vertical CH3. Display raw travel, independently of control inversion/deadzone.
    def norm(value):
        span = high-center if value >= center else center-low
        return max(-1.0, min(1.0, (value - center) / span))
    return (norm(channels[0]), norm(channels[1])), (norm(channels[3]), norm(channels[2]))


def camera_snapshot(path, now=None):
    now = time.monotonic() if now is None else now
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        data = {}
    alive = 0 <= now-data.get('published_monotonic', -math.inf) < 1.5
    active = alive and data.get('active', False)
    return {'status': 'CAMERA ON' if active else 'CAMERA OFF',
            'frames': data.get('frames', 0),
            'fps': data.get('tx_fps', 0) if active else 0,
            'peer': data['peer'][0] if active and data.get('peer') else '-'}


def joystick_figure(position, title, label, active):
    figure=mujoco.MjvFigure()
    mujoco.mjv_defaultFigure(figure)
    figure.title=title
    figure.xlabel=label
    figure.flg_ticklabel[:]=0
    figure.flg_extend=0
    figure.flg_legend=0
    figure.gridsize[:]=1
    figure.range[:]=[[-1.25,1.25],[-1.25,1.25]]
    figure.figurergba[:]=[.06,.09,.13,1]
    figure.panergba[:]=[.09,.14,.20,1]
    figure.linewidth=3
    x,y=position
    length=max(1,math.hypot(x,y));x,y=.8*x/length,.8*y/length
    angle=np.linspace(0,2*np.pi,65)
    lines=[(np.cos(angle),np.sin(angle)),([-1,1],[0,0]),([0,0],[-1,1]),
           ([0,x],[0,y]),(x+.20*np.cos(angle),y+.20*np.sin(angle))]
    for i,(xx,yy) in enumerate(lines):
        n=len(xx);figure.linepnt[i]=n
        figure.linedata[i,:2*n]=np.column_stack([xx,yy]).ravel()
        figure.linergb[i,:]=[.28,.40,.52] if i<3 else ([.28,.85,.67] if active else [.96,.71,.29])
    return figure


class HudViewer:
    def __init__(self, viewer, path):
        self.viewer, self.path = viewer, path
        self.next_draw = 0
        self.logged_viewport = False
        self.ip='checking...'
        self.next_ip=0

    def __getattr__(self, name):
        return getattr(self.viewer, name)

    def sync(self, *args, **kwargs):
        now = time.monotonic()
        if now>=self.next_ip:
            control=snapshot(self.path, now)
            self.ip=advertised_ip(control.get('owner'))
            self.next_ip=now+5
        if now >= self.next_draw:
            viewport = self.viewer.viewport
            if not self.logged_viewport:
                print(f'== HUD viewport: {viewport}',flush=True)
                self.logged_viewport = True
            if viewport and viewport.width >= 320 and viewport.height >= 230:
                data=snapshot(self.path,now)
                camera=camera_snapshot(Path(self.path).with_name('v7rc-video.json'),now)
                points=sticks(data['channels'],data.get('pwm_min',1000),data.get('pwm_center',1500),data.get('pwm_max',2000))
                size=min(240,(viewport.width-36)//2)
                panel_height=min(450,max(80,viewport.height-254))
                figures=[]
                for i,(title,indices) in enumerate([('LEFT 1/2',(0,1)),('RIGHT 4/3',(3,2))]):
                    a,b=indices
                    fig=joystick_figure(points[i],title,f'X {data["channels"][a]}   Y {data["channels"][b]}',data['active'])
                    rect=mujoco.MjrRect(viewport.left+12+i*(size+12),viewport.bottom+viewport.height-panel_height-236,size,panel_height)
                    figures.append((rect,fig))
                self.viewer.set_figures(figures)
                self.viewer.set_texts([
                    (mujoco.mjtFontScale.mjFONTSCALE_150,mujoco.mjtGridPos.mjGRID_TOPLEFT,
                     f'V7RC RX  {data["fps"]:.0f} FPS\n{data["status"]}\n{camera["status"]}\nTX FRAMES  {camera["frames"]}  ({camera["fps"]:.0f} FPS)\nPEER  {camera["peer"]}', ''),
                    (mujoco.mjtFontScale.mjFONTSCALE_150,mujoco.mjtGridPos.mjGRID_TOPRIGHT,
                     f'V7RC CONNECT\nIP  {self.ip}\nCONTROL UDP  {data.get("port",6188)}\nVIDEO UDP  8800','')])
            self.next_draw = now + 0.1
        return self.viewer.sync(*args, **kwargs)


def main():
    path = os.environ.get("MICRODUCK_HUD_FILE")
    if path:
        launch = mujoco.viewer.launch_passive

        def with_hud(*args, **kwargs):
            return HudViewer(launch(*args, **kwargs), path)

        mujoco.viewer.launch_passive = with_hud
        print(f"== V7RC input HUD: {path}", flush=True)
    from mjlab_microduck.sim import body_server
    from microduck_camera import install
    install(body_server)
    body_server.main()


if __name__ == "__main__":
    main()
