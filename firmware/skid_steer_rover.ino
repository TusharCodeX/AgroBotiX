/*
 * =========================================================================================
 * AGRI-PATH SKID-STEER ROVER FIRMWARE SKELETON (ESP32 / ARDUINO)
 * 
 * ⚠️ WARNING: THIS FIRMWARE SKELETON IS UNTESTED ON REAL HARDWARE.
 * ALWAYS PERFORM INITIAL BENCH TESTING WITH THE ROVER CHASSIS PROPPED UP ON STANDS
 * (WHEELS OFF THE GROUND) AND CUTTING BLADES COMPLETELY REMOVED!
 * =========================================================================================
 * 
 * Kinematics: 6-Wheel Skid-Steer Differential Drive (3 wheels per side).
 * Tool: Dual Front Cutting Blades on Servo Arm + DC Cutting Motor.
 * Sensors: Quadrature Encoders (Left & Right), IMU (MPU6050 / BNO055 via I2C).
 * Host Interface: Serial USB / UART @ 115200 baud.
 * 
 * Line Protocol (distances in mm, angles in deg):
 *   F<dist_mm>   -> Forward (e.g. F400 = 40cm)
 *   B<dist_mm>   -> Backward (e.g. B100 = 10cm)
 *   TL<deg>      -> Turn Left in-place (e.g. TL90)
 *   TR<deg>      -> Turn Right in-place (e.g. TR90)
 *   BD           -> Blade Down (Servo lowered)
 *   BU           -> Blade Up (Servo raised)
 *   BON          -> Blade Motor ON (Relay/MOSFET)
 *   BOFF         -> Blade Motor OFF
 *   STOP         -> Controlled stop
 *   ESTOP        -> Immediate cut of all motors and blades
 *   PING         -> Heartbeat message from Raspberry Pi / Host
 * 
 * Safety Watchdog:
 *   Firmware shuts down drive motors AND cutting blades if no valid heartbeat
 *   (PING or command) is received within 500 milliseconds.
 */

#include <Arduino.h>
#include <Wire.h>

// --- PIN DEFINITIONS (Adjust for your specific ESP32/Arduino board) ---
// Left Drive Motors (PWM + Direction)
const int PIN_LEFT_PWM  = 18;
const int PIN_LEFT_DIR1 = 19;
const int PIN_LEFT_DIR2 = 21;

// Right Drive Motors (PWM + Direction)
const int PIN_RIGHT_PWM  = 22;
const int PIN_RIGHT_DIR1 = 23;
const int PIN_RIGHT_DIR2 = 25;

// Front Cutting Blades
const int PIN_BLADE_SERVO = 26; // PWM for lift servo
const int PIN_BLADE_MOTOR = 27; // MOSFET / Relay gate for cutting motors

// Encoders
const int PIN_ENC_LEFT_A  = 34;
const int PIN_ENC_LEFT_B  = 35;
const int PIN_ENC_RIGHT_A = 32;
const int PIN_ENC_RIGHT_B = 33;

// --- CONFIGURATION & CALIBRATION ---
const float MM_PER_TICK = 0.55;         // Calibrate with wheel circumference
const float WHEEL_BASE_MM = 250.0;      // Distance between left and right track centers
const unsigned long WATCHDOG_MS = 500;  // 500ms safety timeout

// State Variables
volatile long g_enc_left_ticks = 0;
volatile long g_enc_right_ticks = 0;
unsigned long g_last_heartbeat_time = 0;
bool g_estopped = false;
bool g_blade_down = false;
bool g_blade_on = false;

// Function Prototypes
void handleCommand(String line);
void setMotors(int left_pwm, int right_pwm);
void stopAll();
void emergencyStop();
void setBladePosition(bool down);
void setBladeMotor(bool on);

void IRAM_ATTR isrLeftEncoder() {
  if (digitalRead(PIN_ENC_LEFT_B) == HIGH) g_enc_left_ticks++;
  else g_enc_left_ticks--;
}

void IRAM_ATTR isrRightEncoder() {
  if (digitalRead(PIN_ENC_RIGHT_B) == HIGH) g_enc_right_ticks++;
  else g_enc_right_ticks--;
}

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 2000);

  // Motor pin modes
  pinMode(PIN_LEFT_PWM, OUTPUT);
  pinMode(PIN_LEFT_DIR1, OUTPUT);
  pinMode(PIN_LEFT_DIR2, OUTPUT);

  pinMode(PIN_RIGHT_PWM, OUTPUT);
  pinMode(PIN_RIGHT_DIR1, OUTPUT);
  pinMode(PIN_RIGHT_DIR2, OUTPUT);

  pinMode(PIN_BLADE_SERVO, OUTPUT);
  pinMode(PIN_BLADE_MOTOR, OUTPUT);

  // Encoders
  pinMode(PIN_ENC_LEFT_A, INPUT_PULLUP);
  pinMode(PIN_ENC_LEFT_B, INPUT_PULLUP);
  pinMode(PIN_ENC_RIGHT_A, INPUT_PULLUP);
  pinMode(PIN_ENC_RIGHT_B, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(PIN_ENC_LEFT_A), isrLeftEncoder, RISING);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_RIGHT_A), isrRightEncoder, RISING);

  // Safe initial state: Motors OFF, Blade UP and OFF
  stopAll();
  setBladePosition(false);
  setBladeMotor(false);

  g_last_heartbeat_time = millis();
  Serial.println("AGRIPATH_ROVER_READY");
}

void loop() {
  // Check Safety Watchdog
  if (millis() - g_last_heartbeat_time > WATCHDOG_MS) {
    if (!g_estopped && (g_blade_on || digitalRead(PIN_LEFT_PWM) > 0 || digitalRead(PIN_RIGHT_PWM) > 0)) {
      emergencyStop();
      Serial.println("ERR WATCHDOG_HEARTBEAT_TIMEOUT");
    }
  }

  // Parse Serial Commands
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      g_last_heartbeat_time = millis(); // Refresh watchdog timer
      handleCommand(line);
    }
  }
}

void handleCommand(String line) {
  if (line == "PING") {
    Serial.println("PONG");
    return;
  }

  if (line == "ESTOP") {
    emergencyStop();
    Serial.println("OK");
    return;
  }

  if (line == "STOP") {
    stopAll();
    Serial.println("OK");
    return;
  }

  if (g_estopped) {
    Serial.println("ERR ROVER_IN_ESTOP");
    return;
  }

  // Blade controls
  if (line == "BD") {
    setBladePosition(true);
    Serial.println("OK");
    return;
  }
  if (line == "BU") {
    setBladePosition(false);
    Serial.println("OK");
    return;
  }
  if (line == "BON") {
    setBladeMotor(true);
    Serial.println("OK");
    return;
  }
  if (line == "BOFF") {
    setBladeMotor(false);
    Serial.println("OK");
    return;
  }

  // Motion commands
  if (line.startsWith("F")) {
    int dist_mm = line.substring(1).toInt();
    driveStraight(dist_mm, true);
    Serial.println("DONE");
    return;
  }
  if (line.startsWith("B")) {
    int dist_mm = line.substring(1).toInt();
    driveStraight(dist_mm, false);
    Serial.println("DONE");
    return;
  }
  if (line.startsWith("TL")) {
    int deg = line.substring(2).toInt();
    pivotInPlace(deg, true);
    Serial.println("DONE");
    return;
  }
  if (line.startsWith("TR")) {
    int deg = line.substring(2).toInt();
    pivotInPlace(deg, false);
    Serial.println("DONE");
    return;
  }

  Serial.println("ERR UNKNOWN_COMMAND");
}

void driveStraight(int dist_mm, bool forward) {
  long target_ticks = (long)(dist_mm / MM_PER_TICK);
  long start_left = g_enc_left_ticks;
  long start_right = g_enc_right_ticks;

  int base_pwm = 160;
  if (!forward) base_pwm = -base_pwm;

  while (abs(g_enc_left_ticks - start_left) < target_ticks) {
    // Watchdog check during execution
    if (millis() - g_last_heartbeat_time > WATCHDOG_MS) {
      emergencyStop();
      return;
    }
    // Proportional encoder sync
    long delta = (g_enc_left_ticks - start_left) - (g_enc_right_ticks - start_right);
    int left_speed = constrain(base_pwm - delta * 2, -255, 255);
    int right_speed = constrain(base_pwm + delta * 2, -255, 255);

    setMotors(left_speed, right_speed);
    delay(10);
  }
  stopAll();
}

void pivotInPlace(int deg, bool turn_left) {
  // Skid-steer in-place pivot: opposite wheel directions
  float arc_len = (PI * WHEEL_BASE_MM * deg) / 360.0;
  long target_ticks = (long)(arc_len / MM_PER_TICK);

  long start_left = g_enc_left_ticks;
  long start_right = g_enc_right_ticks;
  int turn_pwm = 175;

  while (abs(g_enc_left_ticks - start_left) < target_ticks) {
    if (millis() - g_last_heartbeat_time > WATCHDOG_MS) {
      emergencyStop();
      return;
    }
    if (turn_left) {
      setMotors(-turn_pwm, turn_pwm);
    } else {
      setMotors(turn_pwm, -turn_pwm);
    }
    delay(10);
  }
  stopAll();
}

void setMotors(int left_pwm, int right_pwm) {
  // Left Motor
  if (left_pwm >= 0) {
    digitalWrite(PIN_LEFT_DIR1, HIGH);
    digitalWrite(PIN_LEFT_DIR2, LOW);
    analogWrite(PIN_LEFT_PWM, left_pwm);
  } else {
    digitalWrite(PIN_LEFT_DIR1, LOW);
    digitalWrite(PIN_LEFT_DIR2, HIGH);
    analogWrite(PIN_LEFT_PWM, -left_pwm);
  }

  // Right Motor
  if (right_pwm >= 0) {
    digitalWrite(PIN_RIGHT_DIR1, HIGH);
    digitalWrite(PIN_RIGHT_DIR2, LOW);
    analogWrite(PIN_RIGHT_PWM, right_pwm);
  } else {
    digitalWrite(PIN_RIGHT_DIR1, LOW);
    digitalWrite(PIN_RIGHT_DIR2, HIGH);
    analogWrite(PIN_RIGHT_PWM, -right_pwm);
  }
}

void setBladePosition(bool down) {
  g_blade_down = down;
  // Servo pulse: approx 1000us (UP) vs 2000us (DOWN)
  analogWrite(PIN_BLADE_SERVO, down ? 200 : 80);
}

void setBladeMotor(bool on) {
  g_blade_on = on;
  digitalWrite(PIN_BLADE_MOTOR, on ? HIGH : LOW);
}

void stopAll() {
  setMotors(0, 0);
}

void emergencyStop() {
  g_estopped = true;
  stopAll();
  setBladeMotor(false);
  setBladePosition(false);
}
