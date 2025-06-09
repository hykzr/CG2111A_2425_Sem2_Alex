import json
import socket
import ssl
import struct
import sys
import time
from alex_display_node import lidarDisplayProcess
from alex_slam_node import slamThread
from threading import Barrier
from multiprocessing import Barrier as mBarrier
from pubsub.pub_sub_manager import ManagedPubSubRunnable, PubSubManager, getCurrentExecutionContext, publish
import traceback
from utils import *
# constants
NET_ERROR_PACKET = 0
NET_STATUS_PACKET = 1
NET_MESSAGE_PACKET = 2
NET_COMMAND_PACKET = 3
NET_DEBUG_PACKET = 4
EXPECTED_MESSAGE_SIZE = 9
LIDAR_SCAN_TOPIC = "lidar/scan"
SLAM_RESET_TOPIC = "slam/reset"
# TLS details
server_ip = '172.20.10.3'
server_port = 5000 
server_hostname = 'mine.com' 
ca_cert = 'signing.pem'
client_cert = 'laptop.crt'
client_key = 'laptop.key'
# Create a secure SSL context
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_cert)
context.load_cert_chain(certfile=client_cert, keyfile=client_key)
context.check_hostname = False
context.verify_mode = ssl.CERT_OPTIONAL
ssock:ssl.SSLSocket = None
# Create Lidar cache
lidar_cache = []
lidar_cache_cnt = 0
lidar_cache_loading = False
def send_dbg_msg(ssock: ssl.SSLSocket, msg:str):
    """
    Send Debug Message to RPi (max 9 bytes), it should echo the message
    Args:
        ssock (ssl.SSLSocket): tls socket
        msg (str): message to send, only first EXPECTED_MESSAGE_SIZE bytes will be sent
    """
    if not ssock:
        print_red("Falied to send debug message: ssocks is None")
        return
    if len(msg)>EXPECTED_MESSAGE_SIZE:
        msg = msg[:EXPECTED_MESSAGE_SIZE]
    else:
        while len(msg)<EXPECTED_MESSAGE_SIZE:
            msg+="\0"
    ssock.sendall((chr(NET_DEBUG_PACKET)+msg).encode())
def send_cmd(ssock: ssl.SSLSocket, cmd:int, params1: int = 0, params2: int = 0):
    """
    Send Command to RPi who will then forward it to Arduino
    Args:
        ssock (ssl.SSLSocket): tls socket
        cmd (int): command code
        params1 (int, optional): parameter 1. Defaults to 0.
        params2 (int, optional): parameter 1. Defaults to 0.
    """
    if not ssock:
        print_red("Falied to send message: ssocks is None")
        return
    if type(cmd) == str:
        cmd = ord(cmd)
    to_send = struct.pack('<bbii',NET_COMMAND_PACKET,cmd, params1, params2)
    ssock.sendall(to_send)
def save_lidar_cache():
    """Save Lidar Cache to ./lidar_cache.json"""
    print("Saving lidar cache")
    try:
        with open("lidar_cache.json", "w") as f:
            f.write(json.dumps(lidar_cache))
        print_green("lidar cache saved")
    except Exception as e:
        print_red(f"Failed to save lidar cache: {repr(e)}")
        traceback.print_exc()
def load_lidar_cache():
    """Load Lidar Cache from ./lidar_cache.json"""
    global lidar_cache, lidar_cache_loading
    print("Loading lidar cache")
    #reset slam
    publish(SLAM_RESET_TOPIC, None)
    lidar_cache_loading = True
    try:
        #republishing every scan
        with open("lidar_cache.json", "r") as f:
            lidar_cache = json.load(f)
        for i in lidar_cache:
            publish(LIDAR_SCAN_TOPIC, i)
        print_green("lidar cache loaded")
        
    except FileNotFoundError:
        print_red(f"Cannot find cache file: {repr(e)}")
    except Exception as e:
        print_red(f"Failed to load lidar cache: {repr(e)}")
        traceback.print_exc()
    lidar_cache_loading = False

def handle_arduino_msg(data):
    """handle response from Arduino
    Args:
        data (any): parsed data from arduino
    """
    if data:
        print("\rReceived from Arduino: ",end="")
        print_bold(data)
    else:
        print_green("\rArduino respond OK")
def handle_lidar_msg(data):
    """handle response from Lidar, publish it to LIDAR_SCAN_TOPIC when not loading cache
    For every 4 scans it save one to cache
    Args:
        data (_type_): lidar scan data
    """
    global lidar_cache,lidar_cache_cnt, lidar_cache_loading
    # ignores scans while loading cache, 
    # otherwise two scans will mix and ruin the slam
    if lidar_cache_loading:
        return
    publish(LIDAR_SCAN_TOPIC, data)
    if lidar_cache_cnt%4==0:
        lidar_cache.append(data)
    lidar_cache_cnt+=1
class Packet:
    """class to parse and handle json packet from RPi
    """
    def __init__(self, raw:str):
        self.valid = False
        self.raw = raw
        try:
            js_data = json.loads(raw)
        except:
            print_red(f"\rInvalid Data: {raw}")
            return
        if type(js_data)!=dict:
            print_red(f"\rInvalid Packet: {js_data}")
            return
        self.pkg_type:str = js_data.get("pkg_type", "")
        self.resp_type:str = js_data.get("resp_type", "")
        self.data = js_data.get("data", None)
        self.err = js_data.get("err", None)
        self.valid = True
    def handle(self):
        if not self.valid:
            print_orange("\rIgnoring Invalid Data")
        if self.pkg_type == 'err' or self.resp_type=='err':
            print_red(f"\rReceived Error Message From RPi: {self.data} - {self.err}")
        elif self.pkg_type == 'resp':
            if self.resp_type == "arduino":
                handle_arduino_msg(self.data)
        elif self.pkg_type == 'msg':
            if not self.data:
                print_orange("\rReceived Empty Message from RPi")
                return
            if self.resp_type == "arduino":
                handle_arduino_msg(self.data)
            elif self.resp_type == "lidar":
                handle_lidar_msg(self.data)
            elif self.resp_type == "debug":
                print(f"\rReceived Debug Message from RPi: ",end="")
                print_bold(self.data)
            else:
                print_orange(f"\rReceived Data with Unknown Response Type: {self.resp_type}")
        else:
            print_orange(f"\rReceived Data with Unknown Packet Type: {self.pkg_type}")
def handle_connection(ssock: ssl.SSLSocket):
    """Read loop for TLS socket.
    Args:
        ssock (ssl.SSLSocket): tls socket
    """
    ctx:ManagedPubSubRunnable = getCurrentExecutionContext()
    try:
        send_dbg_msg(ssock, "Hello RPi")
        data=""
        while not ctx.isExit():
            try:
                data += ssock.recv(4096).decode()
            except TimeoutError:
                print_orange("\rTLS connection timeout, reconnecting...")
                pass
            except OSError:
                print_orange("\rTLS disconnected, reconnecting...")
                return
            if not data or data[-1]!="}":
                #json packages end with '}' and the data we send does not contain '}'
                continue
            p=Packet(data)
            p.handle()
            data=""
    except ssl.SSLError as e:
        print_red(f"\rSSL Error: {repr(e)}")
        traceback.print_exc()
    except Exception as e:
        print_red(f"\rError: {repr(e)}")
        traceback.print_exc()
def sendCommandThread(setupBarrier:Barrier=None, readyBarrier:Barrier=None):
    """Thread to send commands from keyboard input to the Raspberry Pi via TLS.

    Args:
        setupBarrier (Barrier, optional): A threading barrier to synchronize the start of the thread setup.
        readyBarrier (Barrier, optional): A threading barrier to synchronize the thread start.
                                          If provided, the thread will wait for all parties to be ready before proceeding.
    """
    global ssock, arduino_responded, lidar_cache, lidar_cache_cnt
    ctx:ManagedPubSubRunnable = getCurrentExecutionContext()
    setupBarrier.wait() if readyBarrier != None else None
    print_green(f"\rCLI Thread Ready.")
    readyBarrier.wait() if readyBarrier != None else None
    try:
        while(not ctx.isExit()):
            try:
                while not ssock:
                    if ctx.isExit(): break
                    time.sleep(0.01)
                input_str = get_key_command().strip()
                if ctx.isExit(): break                
                if not input_str: continue
                print("\rCommand: ", input_str)
                if ctx.isExit(): break
                if not input_str: continue
                if input_str[0] == 'u':
                    print_orange("Request restarting Arduino")
                    send_dbg_msg(ssock, "reArduino") # Soft restart Arduino
                elif input_str[0] == 'c':
                    ssock.close() # Close TLS socket and wait for reconnection
                elif input_str[0] == 't':
                    to_send = input("\rPlease input debug message to send: ")
                    print("\rSending Debug Message:", to_send)
                    send_dbg_msg(ssock, to_send)
                elif input_str[0] == '.':
                    publish(SLAM_RESET_TOPIC,None)
                    lidar_cache = []
                    lidar_cache_cnt = 0
                elif input_str[0] == '[':
                    save_lidar_cache()
                elif input_str[0] == ']':
                    load_lidar_cache()
                elif input_str[0] in "fblrscgqoe":
                    try:
                        split_input = [int(x) for x in input_str[1:].strip().split(" ") if x != ""]
                    except:
                        print_red("\rInvalid Arguments")
                        continue
                    p1=p2=0
                    if len(split_input)>=1: 
                        p1=split_input[0]
                        if len(split_input)>=2: 
                            p2=split_input[1]
                    send_cmd(ssock, input_str[0], p1,p2)
                else:
                    print_red("\rInvalid Input")
                time.sleep(0.1)
            except ssl.SSLEOFError:
                ssock.close()
    except (KeyboardInterrupt, EOFError):
        print_orange("\rDetected Ctrl+C, Kill CLI Thread")
    except Exception as e:
        print_red(f"\rCLI Thread Exception: {repr(e)}")
        traceback.print_exc()
    ctx.doExit()
    print_orange("\rExiting Command Thread")
def TLSRecvThread(setupBarrier:Barrier=None, readyBarrier:Barrier=None):
    """Thread to handle messages sent from RPi.
    Args:
        setupBarrier (Barrier, optional): A threading barrier to synchronize the start of the thread setup.
        readyBarrier (Barrier, optional): A threading barrier to synchronize the thread start.
                                          If provided, the thread will wait for all parties to be ready before proceeding.
    """
    global ssock
    ctx:ManagedPubSubRunnable = getCurrentExecutionContext()
    setupBarrier.wait() if readyBarrier != None else None
    readyBarrier.wait() if readyBarrier != None else None
    while not ctx.isExit():
        try:
            with socket.create_connection((server_ip, server_port),3) as sock:
                print_green("\rTLS Connected")
                ssock= context.wrap_socket(sock, server_hostname=server_hostname)
                print_green(f"\rConnected to {server_ip} with TLS")
                ssock.settimeout(2)
                handle_connection(ssock)
        except ConnectionRefusedError:
            print_red("\rConnection refused, reconnecting")
            time.sleep(1)
        except KeyboardInterrupt:
            print_orange("\rDetected Ctrl+C, Kill Client")
            break
        except TimeoutError:
            print_orange("\rTimeout. Reconnecting...")
        except OSError:
            print_red("\rConnection failed, reconnecting")
    ctx.doExit()
    print_orange("\rExiting TLS Client Thread")
def main():
    print("==============SETTING UP REMOTE CLIENT==============")
    with PubSubManager() as mgr:
        uiProcesses = 1
        setupBarrier_ui_m = mBarrier(uiProcesses + 1)
        readyBarrier_ui_m = mBarrier(uiProcesses + 1)
        slamNodes = 1
        setupBarrier_slam_t = Barrier(slamNodes + 1)
        readyBarrier_slam_t = Barrier(slamNodes + 1)
        uiThreads = 1
        setupBarrier_ui_t = Barrier(uiThreads + 1)
        readyBarrier_ui_t = Barrier(uiThreads + 1)
        networkTLSNodes = 1
        setupBarrierNetworkTLS_t = Barrier(networkTLSNodes + 1)
        readyBarrierNetworkTLS_t = Barrier(networkTLSNodes + 1)
        mgr.add_thread(target=slamThread, 
            name="SLAM Thread",
            kwargs={"setupBarrier": setupBarrier_slam_t, "readyBarrier": readyBarrier_slam_t})
        mgr.add_process(target=lidarDisplayProcess, 
            name="Lidar Display Process",
            kwargs={"setupBarrier": setupBarrier_ui_m, "readyBarrier": readyBarrier_ui_m})
        mgr.add_thread(target=sendCommandThread, 
            name="Remote CLI Thread",
            kwargs={"setupBarrier": setupBarrier_ui_t, "readyBarrier": readyBarrier_ui_t})
        mgr.add_thread(target=TLSRecvThread, 
            name="TLS Relay Receive Thread",
            kwargs={"setupBarrier": setupBarrierNetworkTLS_t, "readyBarrier": readyBarrierNetworkTLS_t})
        mgr.start_all()
        setupBarrier_slam_t.wait()
        readyBarrier_slam_t.wait()
        setupBarrierNetworkTLS_t.wait()
        readyBarrierNetworkTLS_t.wait()
        setupBarrier_ui_m.wait()
        readyBarrier_ui_m.wait()
        setupBarrier_ui_t.wait()
        readyBarrier_ui_t.wait()
        mgr.join_all()
if __name__ == '__main__':
    main()
    sys.exit(0)