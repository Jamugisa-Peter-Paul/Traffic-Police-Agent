/*
 * Traffic Light Controller — ESP8266
 * 
 * Dual-mode traffic light:
 *   AUTO mode:   Normal cycling  RED(4s) → YELLOW(4s) → BLUE(4s) → GREEN(4s)
 *   MANUAL mode: Overridden by HTTP commands from the Python pose-detection app
 *                Returns to AUTO after 10s of no commands
 *
 * Hardware:
 *   D1 (GPIO5)  → Relay 1 → RED    bulb (AC 175-265V 5W)
 *   D2 (GPIO4)  → Relay 2 → YELLOW bulb
 *   D5 (GPIO14) → Relay 3 → GREEN  bulb
 *   D6 (GPIO12) → Relay 4 → BLUE   bulb
 *
 * HTTP Endpoints:
 *   GET /set?state=RED|GREEN|YELLOW|BLUE|OFF   → override to manual
 *   GET /status                           → JSON current state & mode
 *
 * ⚠️  CHANGE the WiFi credentials below before flashing!
 */

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

// ============================================================
// CONFIGURATION — CHANGE THESE
// ============================================================
const char* WIFI_SSID     = "Traffic";
const char* WIFI_PASSWORD = "gulugoestoschool";
// ============================================================
// PIN DEFINITIONS (active LOW relays)
// Using raw GPIO numbers for ESP8285/ESP8266 compatibility
// ============================================================
#define RED_PIN    5    // GPIO5  (labeled D1 on NodeMCU)
#define YELLOW_PIN 4    // GPIO4  (labeled D2 on NodeMCU)
#define GREEN_PIN  14   // GPIO14 (labeled D5 on NodeMCU)
#define BLUE_PIN   12   // GPIO12 (labeled D6 on NodeMCU)

// ============================================================
// TIMING (milliseconds)
// ============================================================
#define RED_DURATION      4000   //  4 seconds
#define YELLOW_DURATION   4000   //  4 seconds
#define BLUE_DURATION     4000   //  4 seconds
#define GREEN_DURATION    4000   //  4 seconds

#define MANUAL_TIMEOUT   10000   // Return to AUTO after 10s of no commands

// ============================================================
// STATE
// ============================================================
enum LightState { STATE_RED, STATE_YELLOW, STATE_BLUE, STATE_GREEN, STATE_OFF };
enum Mode       { MODE_AUTO, MODE_MANUAL };

LightState currentState = STATE_RED;
Mode       currentMode  = MODE_AUTO;

unsigned long lastAutoSwitch   = 0;   // Last time auto-mode changed state
unsigned long lastManualCommand = 0;  // Last time a manual command arrived

ESP8266WebServer server(80);

// ============================================================
// RELAY CONTROL
// ============================================================
void setRelays(bool red, bool yellow, bool blue, bool green) {
  // Active HIGH: HIGH = relay ON, LOW = relay OFF
  digitalWrite(RED_PIN,    red    ? HIGH : LOW);
  digitalWrite(YELLOW_PIN, yellow ? HIGH : LOW);
  digitalWrite(BLUE_PIN,   blue   ? HIGH : LOW);
  digitalWrite(GREEN_PIN,  green  ? HIGH : LOW);
}

void applyState(LightState state) {
  switch (state) {
    case STATE_RED:    setRelays(true,  false, false, false); break;
    case STATE_YELLOW: setRelays(false, true,  false, false); break;
    case STATE_BLUE:   setRelays(false, false, true,  false); break;
    case STATE_GREEN:  setRelays(false, false, false, true);  break;
    case STATE_OFF:    setRelays(false, false, false, false); break;
  }
  currentState = state;
}

// ============================================================
// AUTO-CYCLE LOGIC
// ============================================================
unsigned long getDuration(LightState state) {
  switch (state) {
    case STATE_RED:    return RED_DURATION;
    case STATE_YELLOW: return YELLOW_DURATION;
    case STATE_BLUE:   return BLUE_DURATION;
    case STATE_GREEN:  return GREEN_DURATION;
    default:           return RED_DURATION;
  }
}

LightState getNextState(LightState state) {
  switch (state) {
    case STATE_RED:    return STATE_YELLOW;
    case STATE_YELLOW: return STATE_BLUE;
    case STATE_BLUE:   return STATE_GREEN;
    case STATE_GREEN:  return STATE_RED;
    default:           return STATE_RED;
  }
}

void handleAutoCycle() {
  unsigned long now = millis();
  if (now - lastAutoSwitch >= getDuration(currentState)) {
    LightState next = getNextState(currentState);
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
    case STATE_BLUE:   return "BLUE";
    case STATE_GREEN:  return "GREEN";
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
  if (s == "BLUE")   return STATE_BLUE;
  if (s == "GREEN")  return STATE_GREEN;
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

  // Initialize relay pins
  pinMode(RED_PIN, OUTPUT);
  pinMode(YELLOW_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);

  // Start with all OFF, then set RED
  setRelays(false, false, false, false);
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
  server.on("/set", handleSet);
  server.on("/status", handleStatus);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("HTTP server started on port 80");

  lastAutoSwitch = millis();
  Serial.println("Starting in AUTO mode: RED");
}

// ============================================================
// SERIAL COMMAND PARSING (USB fallback)
// Accepts: SET:RED, SET:GREEN, SET:YELLOW, SET:OFF, STATUS
// ============================================================
void handleSerialCommands() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.startsWith("SET:")) {
    String stateStr = cmd.substring(4);
    LightState newState = stringToState(stateStr);

    currentMode = MODE_MANUAL;
    lastManualCommand = millis();
    applyState(newState);

    Serial.print("{\"mode\":\"MANUAL\",\"state\":\"");
    Serial.print(stateToString(currentState));
    Serial.println("\"}");
  }
  else if (cmd == "STATUS") {
    Serial.print("{\"mode\":\"");
    Serial.print(modeToString(currentMode));
    Serial.print("\",\"state\":\"");
    Serial.print(stateToString(currentState));
    Serial.println("\"}");
  }
  else {
    Serial.println("{\"error\":\"Unknown command\"}");
  }
}

// ============================================================
// MAIN LOOP
// ============================================================
void loop() {
  server.handleClient();
  handleSerialCommands();

  unsigned long now = millis();

  if (currentMode == MODE_MANUAL) {
    // Check if manual timeout has expired → return to AUTO
    if (now - lastManualCommand >= MANUAL_TIMEOUT) {
      Serial.println("[MANUAL → AUTO] Timeout, resuming auto-cycle from RED");
      currentMode = MODE_AUTO;
      applyState(STATE_RED);
      lastAutoSwitch = now;
    }
  }

  if (currentMode == MODE_AUTO) {
    handleAutoCycle();
  }

  delay(10);  // Small delay to keep things stable
}
