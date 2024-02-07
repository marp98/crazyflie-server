from fastapi import FastAPI, HTTPException
import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie import Crazyflie

app = FastAPI()

URI = 'radio://0/80/2M'
cflib.crtp.init_drivers(enable_debug_driver=False)

scf_global = None

def connect_crazyflie():
    global scf_global
    if scf_global is None:
        try:
            scf_global = SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache'))
            scf_global.open_link()
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    else:
        return True  

def disconnect_crazyflie():
    global scf_global
    if scf_global is not None:
        scf_global.close_link()
        scf_global = None
        return True
    else:
        return False  

@app.post("/connect")
async def connect():
    if connect_crazyflie():
        return {"message": "Crazyflie connected successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to Crazyflie")

@app.post("/disconnect")
async def disconnect():
    if disconnect_crazyflie():
        return {"message": "Crazyflie disconnected successfully"}
    else:
        return {"message": "Crazyflie was not connected"}

@app.post("/takeoff")
async def takeoff():
    global scf_global
    if scf_global is None:
        raise HTTPException(status_code=503, detail="Crazyflie not connected")
    return {"message": "Takeoff sequence initiated"}

