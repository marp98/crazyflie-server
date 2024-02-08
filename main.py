from fastapi import FastAPI, HTTPException
from threading import Event
import time
import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie import Crazyflie
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

URI = 'radio://0/80/2M'
cflib.crtp.init_drivers(enable_debug_driver=False)

scf_global = None
deck_attached_event = Event()

def param_deck_flow(_, value_str):
    value = int(value_str)
    if value:
        deck_attached_event.set()
        print('Deck is attached!')
    else:
        print('Deck is NOT attached!')

def connect_crazyflie():
    global scf_global
    if scf_global is None:
        try:
            scf_global = SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache'))
            scf_global.open_link()
            scf_global.cf.param.add_update_callback(group='deck', name='bcFlow2', cb=param_deck_flow)
            time.sleep(1)
            deck_attached = deck_attached_event.is_set()
            return True, deck_attached  
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False, False  
    else:
        deck_attached = deck_attached_event.is_set()
        return True, deck_attached

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
    success, deck_attached = connect_crazyflie()
    if success:
        return {"message": "Crazyflie connected successfully", "deck_attached": deck_attached}
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

