

#include <AFMotor.h>

// Motor control
#define FRONT_LEFT   2 // M4 on the driver shield
#define FRONT_RIGHT  1 // M1 on the driver shield
#define BACK_LEFT    3 // M3 on the driver shield
#define BACK_RIGHT   4 // M2 on the driver shield

AF_DCMotor motorFL(FRONT_LEFT);
AF_DCMotor motorFR(FRONT_RIGHT);
AF_DCMotor motorBL(BACK_LEFT);
AF_DCMotor motorBR(BACK_RIGHT);

void move(float speed, int direction)
{
  int speed_scaled = (speed/100.0) * 255;
  motorFL.setSpeed(speed_scaled);
  motorFR.setSpeed(speed_scaled);
  motorBL.setSpeed(speed_scaled);
  motorBR.setSpeed(speed_scaled);

  switch(direction)
    {
      case BACK:
        motorFL.run(BACKWARD);
        motorFR.run(BACKWARD);
        motorBL.run(FORWARD);
        motorBR.run(FORWARD); 
      break;
      case GO:
        motorFL.run(FORWARD);
        motorFR.run(FORWARD);
        motorBL.run(BACKWARD);
        motorBR.run(BACKWARD); 
      break;
      case CW:
        motorFL.run(BACKWARD);
        motorFR.run(FORWARD);
        motorBL.run(FORWARD);
        motorBR.run(BACKWARD); 
      break;
      case CCW:
        motorFL.run(FORWARD);
        motorFR.run(BACKWARD);
        motorBL.run(BACKWARD);
        motorBR.run(FORWARD); 
      break;
      case STOP:
      default:
        motorFL.run(STOP);
        motorFR.run(STOP);
        motorBL.run(STOP);
        motorBR.run(STOP); 
    }
}

void forward(float dist, float speed)
{
  if(dist > 0)
  deltaDist = dist;
  else
  deltaDist=9999999;
  newDist=forwardDist + deltaDist;

  dir=(TDirection)FORWARD;
  move(speed, FORWARD);
}

void backward(float dist, float speed)
{
  if(dist > 0)
  deltaDist = dist;
  else
  deltaDist=9999999;
  newDist=reverseDist + deltaDist;
  
  dir=(TDirection)BACKWARD;
  move(speed, BACKWARD);
}

void ccw(float dist, float speed)
{
  if(dist > 0)
  deltaTicks = computeDeltaTicks(dist);
  else
  deltaTicks=9999999;
  targetTicks=leftReverseTicksTurns + deltaTicks;
  
  dir=(TDirection)CCW;
  move(speed, CCW);
}

void cw(float dist, float speed)
{
  if(dist > 0)
  deltaTicks = computeDeltaTicks(dist);
  else
  deltaTicks=9999999;
  targetTicks=rightReverseTicksTurns + deltaTicks;
  
  dir=(TDirection)CW;
  move(speed, CW);
}

void stop()
{
  dir=(TDirection)STOP;
  move(0, STOP);
}
