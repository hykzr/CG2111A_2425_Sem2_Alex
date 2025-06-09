import enum

# typedef enum
# {
# 	NET_ERROR_PACKET=0,
# 	NET_STATUS_PACKET=1,
# 	NET_MESSAGE_PACKET=2,
# 	NET_COMMAND_PACKET=3
# } TNetConstants;


class TNetType(enum.Enum):
    """
    TNetConstants is an enumeration that defines various types of packets used in the system.

    Attributes:
        NET_ERROR_PACKET (0): Represents an error packet type.
        NET_STATUS_PACKET (1): Represents a status packet type.
        NET_MESSAGE_PACKET (2): Represents a message packet type.
        NET_COMMAND_PACKET (3): Represents a command packet type.
        NET_DEBUG_PACKET (4) Represents a debug packet type
    """
    NET_ERROR_PACKET = 0
    NET_STATUS_PACKET = 1
    NET_MESSAGE_PACKET = 2
    NET_COMMAND_PACKET = 3
    NET_DEBUG_PACKET = 4

