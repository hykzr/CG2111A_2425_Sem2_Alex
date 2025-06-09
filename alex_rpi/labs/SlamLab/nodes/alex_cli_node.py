# This node is an example of a simple publisher monitors the input from the user and publishes commands to the "arduino/send" topic.

# Import Python Native Modules. We require the Barrier class from threading to synchronize the start of multiple threads.
from threading import Barrier
import signal

# Import the required pubsub modules. PubSubMsg class to extract the payload from a message.
from pubsub.pub_sub_manager import ManagedPubSubRunnable, PubSubMsg
from pubsub.pub_sub_manager import publish, subscribe, unsubscribe, getMessages, getCurrentExecutionContext

# Import the command parser from the control module
from control.alex_control import parseUserInput
import sys
# Constants
ARDUINO_SEND_TOPIC = "arduino/send"
DEBUG_SEND_TOPIC = "debug/send"
def get_key():
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        first = sys.stdin.read(1)
        
        if first == '\x1b':
            rest = sys.stdin.read(2)  # Read 2 more chars if it's ESC
            return first + rest
        else:
            return first
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
def get_key_command():
    key = get_key()
    if not key:
        return None
    arrow_map = {
        '\x1b[A': "f 20 100",  # Up
        '\x1b[B': "b 20 100",  # Down
        '\x1b[D': "l 50 100",  # Left
        '\x1b[C': "r 50 100",  # Right
    }

    wasd_map = {
        'w': "f 5 90",
        's': "b 5 90",
        'a': "l 5 95",
        'd': "r 5 95",
        'p': 's'
    }

    if key in arrow_map:
        return arrow_map[key]
    elif key in wasd_map:
        return wasd_map[key]
    else:
        return key[0]
def cliThread(setupBarrier:Barrier=None, readyBarrier:Barrier=None):
    """
    Starts a command thread that interacts with the user. Publishes commands to the "arduino/send" topic for the send thread to handle sending the commands to the Arduino.
    
    Args:
        setupBarrier (Barrier, optional): A threading barrier to synchronize initial setup steps. Defaults to None.
        readyBarrier (Barrier, optional): A threading barrier to synchronize the start of the thread. Defaults to None.
    
    The function performs the following steps:
    1. Sets up the execution context.
    2. Waits for setup to complete if barriers are provided.
    3. Initiates a user interaction loop to receive and parse commands.
    4. Exits gracefully when an exit condition is met.

    Note:
        input is a blocking call, so the thread will wait for user input before proceeding. This means that even if the exit condition is met while waiting for input, the thread remains blocked until input is received (i.e., the user enters a command).

    """

    # Perform any setup here
    pass
    ctx:ManagedPubSubRunnable = getCurrentExecutionContext()

    # Perform any setup here
    setupBarrier.wait() if readyBarrier != None else None

    print(f"CLI Thread Ready. Publishing to {ARDUINO_SEND_TOPIC}")

    # Wait for all Threads ready
    readyBarrier.wait() if readyBarrier != None else None

    # User Interaction Loop
    try:
        while(not ctx.isExit()):
            #input_str = input("Command (t=send over tls, f=forward, b=reverse, l=turn left, r=turn right, s=stop, c=clear stats, g=get stats, o = open, e= close, q=exit)\n")
            input_str = get_key_command().strip()
            if not input_str:
                continue
            if ctx.isExit():
                break
            if input_str[0] == 't':
                send_str = input()
                publish(DEBUG_SEND_TOPIC, send_str)
                continue
            parseResult = parseUserInput(input_str, exitFlag=ctx.exitEvent,acceptInput=True)
            # if the parse result is None then the user entered an invalid command
            if parseResult == None:
                # print("Invalid command. Please try again.")
                continue
            else:
                # if the parse result is not None then the user entered a valid command
                # and the command has been published to the "arduino/send" topic
                publish(ARDUINO_SEND_TOPIC, tuple(parseResult))

            # [Optional: Consider enforcing the user to wait for the arduino to respond before sending the next command]
        pass

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"CLI Thread Exception: {e}")
        pass
    
    # Shutdown and exit the thread gracefully
    ctx.doExit()
    print("Exiting Command Thread")
    pass