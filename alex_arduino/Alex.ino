#include <serialize.h>
#include <stdarg.h>
#include "packet.h"
#include "constants.h"
#include <math.h>
#include <Servo.h>
volatile TDirection dir;

/*
 * Alex's configuration constants
 */
//#define PI 3.141592654

#define ALEX_LENGTH 25.7
#define ALEX_BREADTH 16

const float alexDiagonal = 30.27;
const float alexCirc = 90.095;

// Number of ticks per revolution from the 
// wheel encoder.

#define COUNTS_PER_REV      4

// Wheel circumference in cm.
// We will use this to calculate forward/backward distance traveled 
// by taking revs * WHEEL_CIRC

#define WHEEL_CIRC          22.5f
#define USING_PI 1
/*
 *    Alex's State Variables
 */

// Store the ticks from Alex's left and
// right encoders.
volatile unsigned long leftForwardTicks; 
volatile unsigned long rightForwardTicks;
volatile unsigned long leftReverseTicks; 
volatile unsigned long rightReverseTicks;

//store counters for turning
volatile unsigned long leftForwardTicksTurns; 
volatile unsigned long rightForwardTicksTurns;
volatile unsigned long leftReverseTicksTurns; 
volatile unsigned long rightReverseTicksTurns;

// Store the revolutions on Alex's left
// and right wheels
volatile unsigned long leftRevs;
volatile unsigned long rightRevs;

// Forward and backward distance traveled
volatile unsigned long forwardDist;
volatile unsigned long reverseDist;

volatile unsigned long deltaDist;
volatile unsigned long newDist;
volatile unsigned long deltaTicks;
volatile unsigned long targetTicks;

//varables for color sensor
static volatile ColorSensor currentColorRead = RED;
static volatile uint32_t redVal = 0;
static volatile uint32_t greenVal = 0;
static volatile uint32_t blueVal = 0;
static volatile uint32_t whiteVal = 0;
static volatile uint32_t previousColorRead = 0;
static volatile uint8_t blockColorSensor = 0;
static volatile uint8_t firstEdgeRead = 0;

// servo objects
Servo servoLeft;
Servo servoRight;
Servo servoMedpack;
const int SERVO_LEFT_PIN = 44;
const int SERVO_RIGHT_PIN = 46;
const int SERVO_MEDPACK_PIN = 45;

/*
 * 
 * Alex Communication Routines.
 * 
 */
 

unsigned long computeDeltaTicks(float ang){
  //ang should be >= 22.5
  auto result = (unsigned long)((ang * alexCirc * COUNTS_PER_REV) / (360.0f * WHEEL_CIRC));
  return result>=1?result:1;
}
 
void left(float ang, float speed){
  if(ang == 0)
    deltaTicks=99999999;
  else
    deltaTicks=computeDeltaTicks(ang);
  targetTicks = leftReverseTicksTurns + deltaTicks;
  dir=(TDirection)LEFT;
  //dbprintf("Left: ang=%f, deltaTicks=%lu, targetTicks=%lu", ang, deltaTicks, targetTicks);
  move(speed, CCW);
}

void right(float ang, float speed){
  if(ang == 0)
    deltaTicks=99999999;
  else
    deltaTicks=computeDeltaTicks(ang);
  targetTicks = rightReverseTicksTurns + deltaTicks;
  dir=(TDirection)RIGHT;
  //dbprintf("Right: ang=%f, deltaTicks=%lu, targetTicks=%lu", ang, deltaTicks, targetTicks);
  move(speed, CW);
}

TResult readPacket(TPacket *packet)
{
    // Reads in data from the serial port and
    // deserializes it.Returns deserialized
    // data in "packet".
    
    char buffer[PACKET_SIZE];
    int len;

    len = readSerial(buffer);

    if(len == 0)
      return PACKET_INCOMPLETE;
    else
      return deserialize(buffer, len, packet);
    
}

void sendStatus()
{
  TPacket statusPackage;
  statusPackage.packetType=PACKET_TYPE_RESPONSE;
  statusPackage.command=RESP_STATUS;
  statusPackage.params[0] = leftForwardTicks;
  statusPackage.params[1] = rightForwardTicks;
  statusPackage.params[2] = leftReverseTicks;
  statusPackage.params[3] = rightReverseTicks;
  statusPackage.params[4] = leftForwardTicksTurns;
  statusPackage.params[5] = rightForwardTicksTurns;
  statusPackage.params[6] = leftReverseTicksTurns;
  statusPackage.params[7] = rightReverseTicksTurns;
  statusPackage.params[8] = forwardDist;
  statusPackage.params[9] = reverseDist;
  blockColorSensor = 1;
  firstEdgeRead = 0;
  statusPackage.params[10] = redVal;
  statusPackage.params[11] = greenVal;
  statusPackage.params[12] = blueVal;
  statusPackage.params[13] = whiteVal;
  blockColorSensor = 0;
  statusPackage.params[14] = deltaTicks;
  statusPackage.params[15] = targetTicks;
  
sendResponse(&statusPackage);

}

void sendMessage(const char *message)
{
  // Sends text messages back to the Pi. Useful
  // for debugging.
  
  TPacket messagePacket;
  messagePacket.packetType=PACKET_TYPE_MESSAGE;
  strncpy(messagePacket.data, message, MAX_STR_LEN);
  sendResponse(&messagePacket);
}

void dbprintf(char *format, ...) {
  va_list args;
  char buffer[128];
  va_start(args, format);
  vsprintf(buffer, format, args);
#if USING_PI
  sendMessage(buffer);
#else
  //Serial.println(buffer);
#endif
}

void sendBadPacket()
{
  // Tell the Pi that it sent us a packet with a bad
  // magic number.
  
  TPacket badPacket;
  badPacket.packetType = PACKET_TYPE_ERROR;
  badPacket.command = RESP_BAD_PACKET;
  sendResponse(&badPacket);
  
}

void sendBadChecksum()
{
  // Tell the Pi that it sent us a packet with a bad
  // checksum.
  
  TPacket badChecksum;
  badChecksum.packetType = PACKET_TYPE_ERROR;
  badChecksum.command = RESP_BAD_CHECKSUM;
  sendResponse(&badChecksum);  
}

void sendBadCommand()
{
  // Tell the Pi that we don't understand its
  // command sent to us.
  
  TPacket badCommand;
  badCommand.packetType=PACKET_TYPE_ERROR;
  badCommand.command=RESP_BAD_COMMAND;
  sendResponse(&badCommand);
}

void sendBadResponse()
{
  TPacket badResponse;
  badResponse.packetType = PACKET_TYPE_ERROR;
  badResponse.command = RESP_BAD_RESPONSE;
  sendResponse(&badResponse);
}

void sendOK()
{
  TPacket okPacket;
  okPacket.packetType = PACKET_TYPE_RESPONSE;
  okPacket.command = RESP_OK;
  sendResponse(&okPacket);  
}

void sendResponse(TPacket *packet)
{
  // Takes a packet, serializes it then sends it out
  // over the serial port.
  char buffer[PACKET_SIZE];
  int len;

  len = serialize(buffer, packet, sizeof(TPacket));
  writeSerial(buffer, len);
}


/*
 * Setup and start codes for external interrupts and 
 * pullup resistors.
 * 
 */
// Enable pull up resistors on pins 18 and 19
void enablePullups()
{
  // Use bare-metal to enable the pull-up resistors on pins
  // 19 and 18. These are pins PD2 and PD3 respectively.
  // We set bits 2 and 3 in DDRD to 0 to make them inputs. 
  DDRD &= ~( (1 << PD2) | (1 << PD3) | (1 << PD0));  // Clear bits to set as input
  PORTD |= (1 << PD2) | (1 << PD3);  // Enable pull-ups

  //output pins to control color sensor
  DDRC |= ((1 << 7) | (1 << 6));
  PORTC = (currentColorRead << 6);


  //set up servo pins
  servoLeft.attach(SERVO_LEFT_PIN);
  servoRight.attach(SERVO_RIGHT_PIN);
  servoMedpack.attach(SERVO_MEDPACK_PIN);

  openClaw();
  holdMedpack();
}



//servo functions
void openClaw() {
  servoLeft.write(100);
  servoRight.write(90);
}
void dropMedpack(){
  servoMedpack.write(0);
}
void holdMedpack(){
  servoMedpack.write(102);
}
void closeMedpack(){
  servoMedpack.write(150);
}
void closeClaw(){
  servoLeft.write(46);
  servoRight.write(144);
}

// Functions to be called by INT2 and INT3 ISRs.
void leftISR()
{
  if (dir==FORWARD){
    leftForwardTicks++;
    forwardDist = (unsigned long) ((float) leftForwardTicks / COUNTS_PER_REV * WHEEL_CIRC);
    //dbprintf("Forward Distance: %lu", forwardDist);
    //Serial.println(forwardDist);
    }
  if (dir==BACKWARD){
    leftReverseTicks++;
    reverseDist = (unsigned long) ((float) leftReverseTicks / COUNTS_PER_REV * WHEEL_CIRC);
    //dbprintf("BackWard Distance: %lu", reverseDist);
  }
  if (dir==LEFT){ //LEFT=CCW
    leftReverseTicksTurns++; 
  }
  if (dir==RIGHT){ //RIGHT=CW
    leftForwardTicksTurns++; 
  }
  //dbprintf("LEFT: ");
  //dbprintf(leftDistance);
  //dbprintf("LEFT Forward: %lu, Reverse: %lu, Turning Forward: %lu, Turning Backward: %lu",leftForwardTicks,leftReverseTicks, leftForwardTicksTurns,leftReverseTicksTurns);
}

void rightISR()
{
  if (dir==FORWARD){
    rightForwardTicks++;}
  if (dir==BACKWARD){
    rightReverseTicks++;
  }
  if (dir==LEFT){
    rightForwardTicksTurns++; 
  }
  if (dir==RIGHT){
    rightReverseTicksTurns++; 
  }
  //dbprintf("RIGHT: );
  //dbprintf(rightDistance);
  //dbprintf("RIGHT Forward: %lu, Reverse: %lu, Turning Forward: %lu, Turning Backward: %lu",rightForwardTicks,rightReverseTicks, rightForwardTicksTurns,rightReverseTicksTurns);
}
ISR(INT3_vect) {
  leftISR();
}
ISR(INT2_vect) {
  rightISR();
}

//ISR to keep track of color
void readColorSensorDelay(){
  if(blockColorSensor == 0){
    if(firstEdgeRead == 0){
      previousColorRead = micros();
      firstEdgeRead = 1;
    } 
    else 
    {
      if(currentColorRead == RED){
        redVal = micros() - previousColorRead;
        currentColorRead = GREEN;
      }
      else if (currentColorRead == GREEN){
        greenVal = micros() - previousColorRead;
        currentColorRead = BLUE;
      }
      else if (currentColorRead == BLUE){
        blueVal =  micros() - previousColorRead;
        currentColorRead = WHITE;
      }
      else{
        whiteVal =  micros() - previousColorRead;
        currentColorRead = RED;
      }
      firstEdgeRead = 0;
      PORTC = (currentColorRead << 6);
      previousColorRead = micros();
    }
  }
}
ISR(INT0_vect){
  readColorSensorDelay();
}




// Set up the external interrupt pins INT2 and INT3
// for falling edge triggered. Use bare-metal.
void setupEINT()
{
  // Use bare-metal to configure pins 18 and 19 to be
  // falling edge triggered. Remember to enable
  // the INT2 and INT3 interrupts.
  // Hint: Check pages 110 and 111 in the ATmega2560 Datasheet.

    EICRA &= ~( (1 << ISC20) | (1 << ISC30) | (1 << ISC01)); // Clear ISC20 and ISC30
    EICRA |= ( (1 << ISC21) | (1 << ISC31) | (1 << ISC01));  // Set ISC21 and ISC31
    EIMSK |= (1 << INT2) | (1 << INT3) | (1 << INT0);
}

// Implement the external interrupt ISRs below.
// INT3 ISR should call leftISR while INT2 ISR
// should call rightISR.


// Implement INT2 and INT3 ISRs above.

/*
 * Setup and start codes for serial communications
 * 
 */
// Set up the serial connection. For now we are using 
// Arduino Wiring, you will replace this later
// with bare-metal code.
void setupSerial()
{
  // To replace later with bare-metal.
  Serial.begin(9600);
  // Change Serial to Serial2/Serial3/Serial4 in later labs when using the other UARTs
}

// Start the serial connection. For now we are using
// Arduino wiring and this function is empty. We will
// replace this later with bare-metal code.

void startSerial()
{
  // Empty for now. To be replaced with bare-metal code
  // later on.
  
}

// Read the serial port. Returns the read character in
// ch if available. Also returns TRUE if ch is valid. 
// This will be replaced later with bare-metal code.

int readSerial(char *buffer)
{

  int count=0;

  // Change Serial to Serial2/Serial3/Serial4 in later labs when using other UARTs

  while(Serial.available())
    buffer[count++] = Serial.read();

  return count;
}

// Write to the serial port. Replaced later with
// bare-metal code

void writeSerial(const char *buffer, int len)
{
  Serial.write(buffer, len);
  // Change Serial to Serial2/Serial3/Serial4 in later labs when using other UARTs
}

/*
 * Alex's setup and run codes
 * 
 */

// Clears all our counters
void clearCounters()
{
  leftForwardTicks=0;
  rightForwardTicks=0;
  leftReverseTicks=0;
  rightReverseTicks=0;
  leftReverseTicksTurns=0;
  rightReverseTicksTurns=0;
  leftForwardTicksTurns=0;
  rightForwardTicksTurns=0;
  leftRevs=0;
  rightRevs=0;
  forwardDist=0;
  reverseDist=0; 
}

// Clears one particular counter
void clearOneCounter(int which)
{
  clearCounters();
}
// Intialize Alex's internal states

void initializeState()
{
  clearCounters();
}

void handleCommand(TPacket *command)
{
  switch(command->command)
  {
    // For movement commands, param[0] = distance, param[1] = speed.
    case COMMAND_FORWARD:
        sendOK();
        forward((double) command->params[0], (float) command->params[1]);
      break;
    case COMMAND_REVERSE:
        sendOK();
        backward((double) command->params[0], (float) command->params[1]);
      break;
     case COMMAND_TURN_LEFT:
        sendOK();
        left((double) command->params[0], (float) command->params[1]);
      break;
     case COMMAND_TURN_RIGHT:
        sendOK();
        right((double) command->params[0], (float) command->params[1]);
      break;
      case COMMAND_STOP:
        sendOK();
        stop();
      break;
      case COMMAND_GET_STATS:
        sendOK();
        sendStatus();
        break;
       case COMMAND_CLEAR_STATS:
        sendOK();
        clearOneCounter(command->params[0]);
        break;
      case COMMAND_OPEN:
        sendOK();
        openClaw();
        dropMedpack();
        delay(500);
        closeMedpack();
        break;
      case COMMAND_CLOSE:
        sendOK();
        closeClaw();
        break;
    default:
      sendBadCommand();
  }
}

void waitForHello()
{
  int exit=0;

  while(!exit)
  {
    TPacket hello;
    TResult result;
    
    do
    {
      result = readPacket(&hello);
    } while (result == PACKET_INCOMPLETE);

    if(result == PACKET_OK)
    {
      if(hello.packetType == PACKET_TYPE_HELLO)
      {
     

        sendOK();
        exit=1;
      }
      else
        sendBadResponse();
    }
    else
      if(result == PACKET_BAD)
      {
        sendBadPacket();
      }
      else
        if(result == PACKET_CHECKSUM_BAD)
          sendBadChecksum();
  } // !exit
}

void setup() {
  // put your setup code here, to run once:

  cli();

  //alexDiagonal = sqrt((ALEX_LENGTH * ALEX_LENGTH) + (ALEX_BREADTH * ALEX_BREADTH));
  //alexDiagonal = 30.27;
  //alexCirc = 90.095;
  setupEINT();
  setupSerial();
  startSerial();
  enablePullups();
  initializeState();
  sei();
}

void handlePacket(TPacket *packet)
{
  switch(packet->packetType)
  {
    case PACKET_TYPE_COMMAND:
      handleCommand(packet);
      break;

    case PACKET_TYPE_RESPONSE:
      break;

    case PACKET_TYPE_ERROR:
      break;

    case PACKET_TYPE_MESSAGE:
      break;

    case PACKET_TYPE_HELLO:
      sendOK();
  }
}

void loop() {
// Uncomment the code below for Step 2 of Activity 3 in Week 8 Studio 2

 //backward(0, 100);
  //Serial.println(dir);
// Uncomment the code below for Week 9 Studio 2


 // put your main code here, to run repeatedly:
  TPacket recvPacket; // This holds commands from the Pi

  TResult result = readPacket(&recvPacket);
  
  if(result == PACKET_OK)
    handlePacket(&recvPacket);
  else
    if(result == PACKET_BAD)
    {
      sendBadPacket();
    }
    else
      if(result == PACKET_CHECKSUM_BAD)
      {
        sendBadChecksum();
      } 

   if(deltaDist > 0)
  {
    if(dir==FORWARD)
    {
      if(forwardDist > newDist)
      {
        deltaDist=0;
        newDist=0;
        stop();
      }
    }
  else
    if(dir == BACKWARD)
    {
      if(reverseDist > newDist)
      {
        deltaDist=0;
        newDist=0;
        stop();
      }
    }
  else
    if((Tdir)dir == STOP)
    {
      deltaDist=0;
      newDist=0;
      stop();
    }
  }

  if(deltaTicks > 0)
  {
    if(dir == LEFT)
    {
      if(leftReverseTicksTurns >= targetTicks)
      {
        deltaTicks = 0;
        targetTicks = 0;
        stop();
      }
    }
    else
      if (dir == RIGHT)
      {
        if(rightReverseTicksTurns >= targetTicks)
        {
          deltaTicks = 0;
          targetTicks = 0;
          stop();
        }
      }
      else
        if((Tdir)dir == STOP)
        {
          deltaTicks = 0;
          targetTicks = 0;
          stop();
        }
  }
      
}
