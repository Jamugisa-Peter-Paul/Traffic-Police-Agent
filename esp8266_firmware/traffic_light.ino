/*
 * Traffic Light Controller — ESP8266
 * 
 * Dual-mode traffic light:
 *   AUTO mode:   Normal cycling  RED(30s) → YELLOW(5s) → BLUE/pedestrian(5s) → GREEN(25s) → YELLOW(5s) → RED
 *   MANUAL mode: Overridden by HTTP commands from the Python pose-detection app
 *                Returns to AUTO after 10s of no commands
 *
 * Hardware:
 *   D1 (GPIO5)  → Relay 1 → RED    bulb (AC 175-265V 5W)
 *   D2 (GPIO4)  → Relay 2 → YELLOW/ORANGE bulb
 *   D5 (GPIO14) → Relay 3 → GREEN  bulb
 *   D6 (GPIO12) → Relay 4 → BLUE   bulb (pedestrian crossing indicator)
 *
 * HTTP Endpoints:
 *   GET /set?state=RED|GREEN|YELLOW|BLUE|OFF   → override to manual
 *   GET /status                                → JSON current state & mode
 *
 * ⚠️  CHANGE the WiFi credentials below before flashing!
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

// ============================================================
// CONFIGURATION — CHANGE THESE
// ============================================================
const char* WIFI_SSID     = "GuluGulu";
const char* WIFI_PASSWORD = "gulugoestoschool";

// ============================================================
// PIN DEFINITIONS
// Using raw GPIO numbers for ESP8285/ESP8266 compatibility
// ============================================================
#define RED_PIN    5    // GPIO5  (labeled D1 on NodeMCU)
#define YELLOW_PIN 4    // GPIO4  (labeled D2 on NodeMCU)
#define GREEN_PIN  14   // GPIO14 (labeled D5 on NodeMCU)
#define BLUE_PIN   12   // GPIO12 (labeled D6 on NodeMCU) — pedestrian blue LED

// ============================================================
// TIMING (milliseconds)
// ============================================================
#define RED_DURATION     30000   // 30 seconds
#define GREEN_DURATION   25000   // 25 seconds
#define YELLOW_DURATION   5000   //  5 seconds
#define BLUE_DURATION     5000   //  5 seconds — pedestrian crossing phase

#define MANUAL_TIMEOUT   10000   // Return to AUTO after 10s of no commands

// ============================================================
// STATE
// Auto cycle: RED → YELLOW → BLUE (pedestrians go) → GREEN → YELLOW → RED
// ============================================================
enum LightState { STATE_RED, STATE_YELLOW, STATE_GREEN, STATE_BLUE, STATE_OFF };
enum Mode       { MODE_AUTO, MODE_MANUAL };

LightState currentState = STATE_RED;
Mode       currentMode  = MODE_AUTO;

unsigned long lastAutoSwitch    = 0;   // Last time auto-mode changed state
unsigned long lastManualCommand = 0;   // Last time a manual command arrived

ESP8266WebServer server(80);

// ============================================================
// RELAY / LED CONTROL
// ============================================================
void setOutputs(bool red, bool yellow, bool green, bool blue) {
  // All outputs go through relays — HIGH = relay ON, LOW = relay OFF
  digitalWrite(RED_PIN,    red    ? HIGH : LOW);
  digitalWrite(YELLOW_PIN, yellow ? HIGH : LOW);
  digitalWrite(GREEN_PIN,  green  ? HIGH : LOW);
  digitalWrite(BLUE_PIN,   blue   ? HIGH : LOW);
}

void applyState(LightState state) {
  switch (state) {
    case STATE_RED:    setOutputs(true,  false, false, false); break;
    case STATE_YELLOW: setOutputs(false, true,  false, false); break;
    case STATE_GREEN:  setOutputs(false, false, true,  false); break;
    case STATE_BLUE:   setOutputs(false, false, false, true);  break;  // pedestrians
    case STATE_OFF:    setOutputs(false, false, false, false); break;
  }
  currentState = state;
}

// ============================================================
// AUTO-CYCLE LOGIC
// Cycle: RED → YELLOW → BLUE → GREEN → YELLOW → RED → ...
// ============================================================
unsigned long getDuration(LightState state) {
  switch (state) {
    case STATE_RED:    return RED_DURATION;
    case STATE_GREEN:  return GREEN_DURATION;
    case STATE_YELLOW: return YELLOW_DURATION;
    case STATE_BLUE:   return BLUE_DURATION;
    default:           return RED_DURATION;
  }
}

LightState getNextState(LightState state) {
  switch (state) {
    case STATE_RED:    return STATE_YELLOW;   // RED    → warn with YELLOW
    case STATE_YELLOW: return STATE_BLUE;     // YELLOW → pedestrians go (BLUE)
    case STATE_BLUE:   return STATE_GREEN;    // BLUE   → vehicles go (GREEN)
    case STATE_GREEN:  return STATE_YELLOW;   // GREEN  → warn with YELLOW
    default:           return STATE_RED;
  }
}

// Tracks whether the current YELLOW phase follows GREEN (→ RED) or RED (→ BLUE)
// We determine this by checking what was active before YELLOW.
// Simpler approach: use a flag.
bool yellowAfterGreen = false;  // true = YELLOW came from GREEN, next is RED

LightState getNextStateWithContext(LightState state) {
  if (state == STATE_YELLOW) {
    if (yellowAfterGreen) {
      yellowAfterGreen = false;
      return STATE_RED;      // YELLOW after GREEN → back to RED
    } else {
      return STATE_BLUE;     // YELLOW after RED → pedestrian BLUE
    }
  }
  if (state == STATE_RED) {
    return STATE_YELLOW;     // RED → YELLOW (warning before pedestrian cross)
  }
  if (state == STATE_BLUE) {
    return STATE_GREEN;      // BLUE → GREEN (vehicles go)
  }
  if (state == STATE_GREEN) {
    yellowAfterGreen = true;
    return STATE_YELLOW;     // GREEN → YELLOW (warning before RED)
  }
  return STATE_RED;
}

void handleAutoCycle() {
  unsigned long now = millis();
  if (now - lastAutoSwitch >= getDuration(currentState)) {
    LightState next = getNextStateWithContext(currentState);
    applyState(next);
    lastAutoSwitch = now;
    Serial.print("[AUTO] Switched to: ");
    Serial.println(stateToString(currentState));
  }
}

// ============================================================
// STRING HELPERS
// ============================================================
const char* stateToString(LightState s) {
  switch (s) {
    case STATE_RED:    return "RED";
    case STATE_YELLOW: return "YELLOW";
    case STATE_GREEN:  return "GREEN";
    case STATE_BLUE:   return "BLUE";
    case STATE_OFF:    return "OFF";
    default:           return "UNKNOWN";
  }
}

const char* modeToString(Mode m) {
  return m == MODE_AUTO ? "AUTO" : "MANUAL";
}

LightState stringToState(String s) {
  s.toUpperCase();
  if (s == "RED")    return STATE_RED;
  if (s == "YELLOW") return STATE_YELLOW;
  if (s == "GREEN")  return STATE_GREEN;
  if (s == "BLUE")   return STATE_BLUE;
  if (s == "OFF")    return STATE_OFF;
  return STATE_RED;  // default fallback
}

// ============================================================
// HTTP HANDLERS
// ============================================================
void handleSet() {
  if (!server.hasArg("state")) {
    server.send(400, "application/json", "{\"error\":\"Missing 'state' parameter\"}");
    return;
  }

  String stateStr = server.arg("state");
  LightState newState = stringToState(stateStr);

  // Switch to manual mode
  currentMode = MODE_MANUAL;
  lastManualCommand = millis();
  applyState(newState);

  Serial.print("[MANUAL] Set to: ");
  Serial.println(stateToString(currentState));

  String json = "{\"mode\":\"MANUAL\",\"state\":\"";
  json += stateToString(currentState);
  json += "\"}";
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

void handleStatus() {
  String json = "{\"mode\":\"";
  json += modeToString(currentMode);
  json += "\",\"state\":\"";
  json += stateToString(currentState);
  json += "\"}";

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

void handleNotFound() {
  server.send(404, "application/json", "{\"error\":\"Not found\"}");
}

// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.println("\n=== Traffic Light Controller ===");

  // Initialize output pins
  pinMode(RED_PIN,    OUTPUT);
  pinMode(YELLOW_PIN, OUTPUT);
  pinMode(GREEN_PIN,  OUTPUT);
  pinMode(BLUE_PIN,   OUTPUT);

  // Start with all OFF, then set RED
  setOutputs(false, false, false, false);
  delay(200);
  applyState(STATE_RED);

  // Connect to WiFi
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 60) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection FAILED! Running in standalone AUTO mode.");
  }

  // Setup HTTP routes
  server.on("/set",    handleSet);
  server.on("/status", handleStatus);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("HTTP server started on port 80");

  lastAutoSwitch = millis();
  Serial.println("Starting in AUTO mode: RED");
  Serial.println("Cycle: RED(30s) → YELLOW(5s) → BLUE/pedestrian(5s) → GREEN(25s) → YELLOW(5s) → RED");
}

// ============================================================
// MAIN LOOP
// ============================================================
void loop() {
  server.handleClient();

  unsigned long now = millis();

  if (currentMode == MODE_MANUAL) {
    // Check if manual timeout has expired → return to AUTO
    if (now - lastManualCommand >= MANUAL_TIMEOUT) {
      Serial.println("[MANUAL → AUTO] Timeout, resuming auto-cycle from RED");
      currentMode = MODE_AUTO;
      yellowAfterGreen = false;
      applyState(STATE_RED);
      lastAutoSwitch = now;
    }
  }

  if (currentMode == MODE_AUTO) {
    handleAutoCycle();
  }

  delay(10);  // Small delay to keep things stable
}
