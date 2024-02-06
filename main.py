from fastapi import FastAPI, BackgroundTasks
from typing import Union
import time
import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie import Crazyflie

app = FastAPI()

URI = 'radio://0/80/2M'
DEFAULT_HEIGHT = 0.3 

cflib.crtp.init_drivers(enable_debug_driver=False)

def take_off_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(2)
        mc.stop()

async def takeoff_background_task():
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        take_off_simple(scf)

@app.post("/takeoff")
async def takeoff(background_tasks: BackgroundTasks):
    background_tasks.add_task(takeoff_background_task)
    return {"message": "Takeoff sequence initiated"}

@app.get("/")
def read_root():
    return {"Crazyflie": "Drone"}

