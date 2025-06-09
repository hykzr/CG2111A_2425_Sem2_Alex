import socket
import ssl
import json
import struct
import threading
# constants
NET_ERROR_PACKET = 0
NET_STATUS_PACKET = 1
NET_MESSAGE_PACKET = 2
NET_COMMAND_PACKET = 3
NET_DEBUG_PACKET = 4
EXPECTED_MESSAGE_SIZE = 9
# TLS details
server_ip = '10.16.248.250'
server_port = 5001  # Change this if your server uses a different port
server_hostname = 'mine.com'  # Must match the CN or SAN in server's cert
ca_cert = 'signing.pem'      # CA that signed the server cert
client_cert = 'laptop.crt'   # Client certificate
client_key = 'laptop.key'    # Client private key
# Create a secure SSL context
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_cert)
context.load_cert_chain(certfile=client_cert, keyfile=client_key)
context.check_hostname = False
context.verify_mode = ssl.CERT_OPTIONAL

kill_threads = False
class Packet:
    def __init__(self, raw:str):
        self.valid = False
        try:
            js_data = json.loads(raw)
        except:
            print(f"Invalid Data: {raw}")
            return
        if type(js_data)!=dict:
            print(f"Invalid Packet: {js_data}")
            return
        self.pkg_type:str = js_data.get("pkg_type", "")
        self.resp_type:str = js_data.get("resp_type", "")
        self.data = js_data.get("data", None)
        self.err = js_data.get("err", None)
        self.valid = True
    def handle(self):
        if not self.valid:
            print("Ignoring Invalid Data")
        if self.pkg_type == 'err' or self.resp_type=='err':
            print(f"Received Error Message From RPi: {self.err}")
        elif self.pkg_type == 'resp':
            return
        elif self.pkg_type == 'msg':
            if not self.data:
                print("Received Empty Message from RPi")
                return
            if self.resp_type == "arduino":
                handle_arduino_msg(self.data)
            elif self.resp_type == "lidar":
                handle_arduino_msg(self.data)
            elif self.resp_type == "debug":
                print(f"Received Debug Message from RPi: {self.data}")
            else:
                print(f"Received Data with Unknown Response Type: {self.resp_type}")
        else:
            print(f"Received Data with Unknown Packet Type: {self.pkg_type}")

def handle_arduino_msg(data):
    print(data)
def handle_lidar_msg(data):
    print(data)
def send_dbg_msg(ssock: ssl.SSLSocket, msg:str):
    """
    Send Debug Message to RPi, it should echo the message
    Args:
        ssock (ssl.SSLSocket): tsl socket
        msg (str): message to send, only first EXPECTED_MESSAGE_SIZE bytes will be sent
    """
    if not ssock:
        print("Falied to send message: ssocks is None")
        return
    if len(msg)>EXPECTED_MESSAGE_SIZE:
        msg = msg[:EXPECTED_MESSAGE_SIZE]
    else:
        while len(msg)<EXPECTED_MESSAGE_SIZE:
            msg+="\0"
    ssock.sendall((chr(NET_DEBUG_PACKET)+msg).encode())
def send_cmd(ssock: ssl.SSLSocket, cmd:int, params1: int = 0, params2: int = 0):
    if not ssock:
        print("Falied to send message: ssocks is None")
        return
    if type(cmd) == str:
        cmd = ord(cmd)
    to_send = struct.pack('<bbii',NET_COMMAND_PACKET,cmd, params1, params2)
    ssock.sendall(to_send)
def remote_main(ssock: ssl.SSLSocket):
    try:
        send_dbg_msg(ssock, "Hello RPi")
        data=""
        while True:
            try:
                data += ssock.recv(4096).decode()
            except TimeoutError:
                continue
            if not data or data[-1]!="}":
                #json packages end with '}' and the data we send does not contain '}'
                continue
            p=Packet(data)
            p.handle()
            data=""
    except ssl.SSLError as e:
        print("SSL Error:", e)
    except Exception as e:
        print("Error:", e)
def remote_cli(ssock: ssl.SSLSocket):
    """Commands:
        f: Move forward. Requires distance in cm and power in %.
        b: Move backward. Requires distance in cm and power in %.
        l: Turn left. Requires degrees to turn and power in %.
        r: Turn right. Requires degrees to turn and power in %.
        s: Stop the movement.
        c: Clear statistics.
        g: Get statistics.
        q: Quit the program and set the exit flag.
        o: open claw
        e: close claw"""
    try:
        while True:
            if kill_threads:
                break
            input_str = input("Command (t=send over tls, f=forward, b=reverse, l=turn left, r=turn right, s=stop, c=clear stats, g=get stats, q=exit)\n")
            if kill_threads:
                break
            if not input_str:
                continue
            if input_str[0] == 't':
                to_send = input_str[1:].strip()
                print("Sending Debug Message:", to_send)
                send_dbg_msg(ssock, to_send)
            elif input_str[0] in "fblrscgqoe":
                split_input = [int(x) for x in input_str[1:].strip().split(" ") if x != ""]
                p1=p2=0
                if len(split_input)>=1: 
                    p1=split_input[0]
                    if len(split_input)>=2: 
                        p2=split_input[1]
                send_cmd(ssock, ord(input_str[0]), p1,p2)
            else:
                print("Invalid Input")
    except KeyboardInterrupt or EOFError:
        print("Detected Ctrl+C, Kill CLI Thread")
        return
    print("Exiting CLI Thread")
if __name__ == "__main__":
    t = None
    while(1):
        try:
            with socket.create_connection((server_ip, server_port),2) as sock:
                print("TLS Connected")
                with context.wrap_socket(sock, server_hostname=server_hostname) as ssock:
                    print(f"Connected to {server_ip} with TLS")
                    kill_threads = False
                    t = threading.Thread(target = remote_cli, args=(ssock,))
                    t.start()
                    remote_main(ssock)
        except KeyboardInterrupt:
            print("Detected Ctrl+C, Kill Client")
            kill_threads = True
            break
        except TimeoutError:
            kill_threads = True
            print("Timeout, waiting thread to shutdown")
            while t and t.is_alive():pass #wait thread to shutdown
            print("Reconnecting...")