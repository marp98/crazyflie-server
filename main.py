from fastapi import FastAPI, HTTPException, WebSocket
from threading import Event
import time
import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
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

def get_stabilizer_parameters(scf):
    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)  # Adjust period as needed
    lg_stab.add_variable('stabilizer.roll', 'float')
    lg_stab.add_variable('stabilizer.pitch', 'float')
    lg_stab.add_variable('stabilizer.yaw', 'float')
    
    stabilizer_data = {}

    def log_stab_callback(timestamp, data, logconf_name):
        # Format each value with 8 decimal places
        for key, value in data.items():
            stabilizer_data[key] = f"{value:.8f}"

    with SyncLogger(scf, lg_stab) as logger:
        lg_stab.data_received_cb.add_callback(log_stab_callback)
        # Wait for at least one set of data to be received
        while not stabilizer_data:
            time.sleep(0.1)

    return stabilizer_data

def get_battery_voltage(scf):
    log_config = LogConfig(name='Battery', period_in_ms=1000)  # Adjust logging period as needed
    log_config.add_variable('pm.vbat', 'float')
    
    battery_voltage = {'voltage': 0.0}

    def battery_voltage_callback(timestamp, data, logconf):
        battery_voltage['voltage'] = f"{data['pm.vbat']:.8f}"

    with SyncLogger(scf, log_config) as logger:
        log_config.data_received_cb.add_callback(battery_voltage_callback)
        # Wait for at least one set of data to be received
        while battery_voltage['voltage'] == 0.0:
            time.sleep(0.1)

    return battery_voltage

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

@app.post("/read_parameters")
async def read_parameters():
    global scf_global
    if scf_global is None:
        raise HTTPException(status_code=503, detail="Crazyflie not connected")
    
    stabilizer_data = get_stabilizer_parameters(scf_global)
    return stabilizer_data

@app.post("/read_battery_voltage")
async def read_battery_voltage():
    global scf_global
    if scf_global is None:
        raise HTTPException(status_code=503, detail="Crazyflie not connected")
    
    try:
        battery_voltage = get_battery_voltage(scf_global)
        return battery_voltage
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading battery voltage: {e}")

async def log_stab_async(websocket: WebSocket, scf: SyncCrazyflie):
    logconf = LogConfig(name='Stabilizer', period_in_ms=10)
    logconf.add_variable('stabilizer.roll', 'float')
    logconf.add_variable('stabilizer.pitch', 'float')
    logconf.add_variable('stabilizer.yaw', 'float')

    def log_stab_callback(timestamp, data, logconf):
        asyncio.create_task(websocket.send_json({"timestamp": timestamp, **data}))

    cf = scf.cf
    cf.log.add_config(logconf)
    logconf.data_received_cb.add_callback(log_stab_callback)
    logconf.start()

    while True:
        await asyncio.sleep(1)
        if websocket.client_state == WebSocket.DISCONNECTED:
            logconf.stop()
            break

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        await log_stab_async(websocket, scf)

@app.post("/takeoff")
async def takeoff():
    global scf_global
    if scf_global is None:
        raise HTTPException(status_code=503, detail="Crazyflie not connected")
    return {"message": "Takeoff sequence initiated"}

