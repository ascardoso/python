/*********************************************************************
 * M5Stack PaperDIY - Weather, Battery & Moon Phase, Tides
 *
 * Features:
 *   - OpenWeatherMap weather data
 *   - Celsius and Fahrenheit with graphical degree symbols
 *   - Weather description and humidity
 *   - Outlined weather icon
 *   - M5PM1 battery voltage and estimated percentage
 *   - Moon phase illustration, name and illumination
 *   - Weather refresh every 10 minutes
 *
 * Libraries:
 *   M5Unified, M5GFX, M5PM1, ArduinoJson
 *********************************************************************/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <M5Unified.h>
#include <M5PM1.h>
#include <time.h>
#include <math.h>

/* --------------------- USER SETTINGS --------------------------- */

const char *ssid     = "";
const char *password  = "";
const char *weatherApiKey = "";

// Alpaca API credentials: use your own paper or live account keys.
const char *alpacaKey    = "";
const char *alpacaSecret = "";

const char *stockSymbol = "";

const char *tideStation = "";  
const char *tideDatum   = "MLLW";

#define INK   TFT_BLACK
#define PAPER TFT_WHITE

const unsigned long fetchInterval = 10UL * 60UL * 1000UL;

/* --------------------- GLOBALS --------------------------------- */

M5PM1 pm1;
bool pm1Ready = false;

unsigned long lastFetch = 0;

struct Weather {
  String city;
  float tempC = 0.0f;
  String description;
  int humidity = 0;
  int cloudCover = -1;
};

Weather weather;

uint16_t batteryMilliVolts = 0;
float batteryVoltage = 0.0f;
int batteryPercent = 0;
bool batteryReadOK = false;

struct StockInfo {
    float bid = 0.0f;
    float ask = 0.0f;
    float price = 0.0f;      // midpoint or ltp
    String timestamp;
    bool valid = false;
};

StockInfo stock;             // global instance
float lastNonZeroQuote = 0f;

// ---------------------------------------------------------------------------
//  Helper struct to hold an event
// ---------------------------------------------------------------------------
struct AstroEvent {
  const char *name;   // "sunrise", "sunset", …
  String      time;   // "07:25:00"
  int         hour;   // parsed integer, for sorting
  int         minute;
};

AstroEvent events[4];
int evCount = 0;

/* --------------------- TIDE DATA ------------------------------- */

struct TideEvent {
  String time;
  String type;       // "H" = high, "L" = low
  float height = 0.0f;
  bool valid = false;
};

struct TideData {
  float height = 0.0f;
  String direction = "Unknown";
  TideEvent nextHigh;
  TideEvent nextLow;
  TideEvent previousEvent;
  TideEvent nextEvent;
  bool valid = false;
};

TideData tide;

// unsigned long lastFetch = 0;
bool clockReady = false;

/* --------------------- BATTERY --------------------------------- */

int mapVoltageToPercent(float voltage) {
  if (voltage >= 4.20f) return 100;
  if (voltage <= 3.70f) return 0;

  return (int)(((voltage - 3.70f) / 0.50f) * 100.0f);
}

bool readBattery() {
  if (!pm1Ready) {
    batteryReadOK = false;
    return false;
  }

  uint16_t mv = 0;
  m5pm1_err_t result = pm1.readVbat(&mv);

  if (result != M5PM1_OK) {
    batteryReadOK = false;
    return false;
  }

  batteryMilliVolts = mv;
  batteryVoltage = mv / 1000.0f;
  batteryPercent = mapVoltageToPercent(batteryVoltage);
  batteryReadOK = true;

  return true;
}

// Return true if now is between 9:30–16:00 Eastern Time on a weekday.
bool marketIsOpen() {
    // 1. Get current UTC time
    time_t now = time(nullptr);          // seconds since Jan‑01‑1970 UTC

    // 2. Convert to Eastern Time (EST/EDT).  
    //    EST = UTC‑5, EDT = UTC‑4.  For a quick demo we ignore DST.
    //    If you need proper DST handling, use <Timezone.h> or a TZ database.
    const int EST_OFFSET = -5 * 3600;     // seconds
    now += EST_OFFSET;

    struct tm local_tm;
#if defined(ESP32) || defined(ARDUINO_ARCH_ESP8266)
    localtime_r(&now, &local_tm);        // thread‑safe on ESP
#else
    localtime_r(&now, &local_tm);
#endif

    // 3. Check weekday (0 = Sunday … 6 = Saturday)
    if (local_tm.tm_wday == 0 || local_tm.tm_wday == 6) return false;

    // 4. Convert hour/minute to minutes since midnight
    int minutes = local_tm.tm_hour * 60 + local_tm.tm_min;

    // Market opens at 9:30 (570 min) and closes at 16:00 (960 min)
    return (minutes >= 9 * 60 + 30) && (minutes < 16 * 60);
}

/* --------------------- WI-FI ----------------------------------- */

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("Connecting to Wi-Fi...");
  WiFi.begin(ssid, password);

  unsigned long start = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - start < 30000UL) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Connected. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi connection timed out.");
  }
}

/* --------------------- TIME HELPERS ---------------------------- */

// Pacific time, including daylight-saving transitions.
void initClock() {
  setenv("TZ", "PST8PDT,M3.2.0,M11.1.0", 1);
  tzset();

  configTime(0, 0, "pool.ntp.org", "time.nist.gov"); // sync in UTC
  setenv("TZ", "PST8PDT,M3.2.0,M11.1.0", 1);         // set local zone
  tzset();                                           // apply it

  Serial.print("Synchronizing clock");

  for (int i = 0; i < 30; i++) {
    if (time(nullptr) > 1700000000) {
      clockReady = true;
      break;
    }

    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println(clockReady ? "Clock synchronized"
                            : "Clock synchronization failed");
}

bool parseTideTime(const char *text, time_t &result) {
  int year, month, day, hour, minute;

  if (sscanf(text, "%d-%d-%d %d:%d",
             &year, &month, &day, &hour, &minute) != 5) {
    return false;
  }

  struct tm t = {};
  t.tm_year = year - 1900;
  t.tm_mon  = month - 1;
  t.tm_mday = day;
  t.tm_hour = hour;
  t.tm_min  = minute;
  t.tm_isdst = -1;

  result = mktime(&t);

  return result != (time_t)-1;
}

String formatTideTime(const String &text) {
  time_t timestamp;

  if (!parseTideTime(text.c_str(), timestamp)) {
    return text;
  }

  struct tm localTime;
  localtime_r(&timestamp, &localTime);

  char buffer[20];
  strftime(buffer, sizeof(buffer), "%I:%M %p", &localTime);

  String result(buffer);
  result.trim();

  if (result.startsWith("0")) {
    result.remove(0, 1);
  }

  return result;
}

void getDateRange(String &startDate, String &endDate) {
  time_t now = time(nullptr);
  struct tm localTime;

  localtime_r(&now, &localTime);

  char today[9];
  char tomorrow[9];

  strftime(today, sizeof(today), "%Y%m%d", &localTime);

  localTime.tm_mday += 1;
  mktime(&localTime);

  strftime(tomorrow, sizeof(tomorrow), "%Y%m%d", &localTime);

  startDate = today;
  endDate = tomorrow;
}

String formatDate() {
  time_t now = time(nullptr);
  struct tm timeInfo;

  localtime_r(&now, &timeInfo);

  const char* suffix = "th";
  int day = timeInfo.tm_mday;

  if (day % 100 < 11 || day % 100 > 13) {
    if (day % 10 == 1) suffix = "st";
    else if (day % 10 == 2) suffix = "nd";
    else if (day % 10 == 3) suffix = "rd";
  }

  char buffer[20];

  strftime(buffer, sizeof(buffer), "%b", &timeInfo);

  String result = String(buffer) + " " +
                  String(day) + suffix + ", " +
                  String(timeInfo.tm_year + 1900);

  return result;
}

/* --------------------- HTTPS JSON REQUEST ---------------------- */

bool fetchNOAAJson(const String &url, JsonDocument &doc) {
  WiFiClientSecure client;

  // Encrypted HTTPS, but without certificate verification.
  // For permanent use, configure a trusted root certificate.
  client.setInsecure();

  HTTPClient http;
  http.setTimeout(15000);

  if (!http.begin(client, url)) {
    Serial.println("Could not start NOAA request");
    return false;
  }

  int code = http.GET();

  if (code != HTTP_CODE_OK) {
    Serial.printf("NOAA HTTP error: %d\n", code);
    http.end();
    return false;
  }

  DeserializationError err =
      deserializeJson(doc, http.getStream());

  http.end();

  if (err) {
    Serial.printf("NOAA JSON error: %s\n", err.c_str());
    return false;
  }

  if (!doc["error"].isNull()) {
    Serial.println("NOAA returned an API error");
    serializeJson(doc["error"], Serial);
    Serial.println();
    return false;
  }

  return true;
}

/* --------------------- CURRENT PREDICTED HEIGHT ---------------- */

// Get the closest predicted tide height at or before now,
// and the next predicted height, to estimate movement.

bool fetchCurrentTide() {
  String startDate, endDate;
  getDateRange(startDate, endDate);

  String url =
      "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
      "?begin_date=" + startDate +
      "&end_date=" + endDate +
      "&station=" + String(tideStation) +
      "&product=predictions"
      "&datum=" + String(tideDatum) +
      "&time_zone=lst_ldt"
      "&units=english"
      "&interval=6"
      "&format=json";

  JsonDocument doc;

  if (!fetchNOAAJson(url, doc)) {
    return false;
  }

  if (doc["predictions"].isNull()) {
    Serial.println("No tide predictions returned");
    return false;
  }

  time_t now = time(nullptr);
  time_t previousTime = 0;
  time_t nextTime = 0;

  float previousHeight = 0.0f;
  float nextHeight = 0.0f;

  for (JsonObject p : doc["predictions"].as<JsonArray>()) {
    const char *timeText = p["t"] | "";
    float height = String(p["v"] | "0").toFloat();

    time_t predictionTime;

    if (!parseTideTime(timeText, predictionTime)) {
      continue;
    }

    if (predictionTime <= now &&
        predictionTime > previousTime) {
      previousTime = predictionTime;
      previousHeight = height;
    }

    if (predictionTime > now &&
        (nextTime == 0 || predictionTime < nextTime)) {
      nextTime = predictionTime;
      nextHeight = height;
    }
  }

  if (previousTime == 0) {
    Serial.println("No previous tide prediction available");
    return false;
  }

  tide.height = previousHeight;

  if (nextTime != 0 && nextTime > previousTime) {
    float change = nextHeight - previousHeight;

    if (change > 0.005f) {
      tide.direction = "Rising";
    } else if (change < -0.005f) {
      tide.direction = "Falling";
    } else {
      tide.direction = "Near steady";
    }
  } else {
    tide.direction = "Unknown";
  }

  tide.valid = true;

  Serial.printf("Predicted tide: %.2f ft, %s\n",
                tide.height, tide.direction.c_str());

  return true;
}

/* --------------------- NEXT HIGH / LOW TIDES ------------------- */

bool fetchHighLowTides() {
  String startDate, endDate;
  getDateRange(startDate, endDate);

  String url =
      "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
      "?begin_date=" + startDate +
      "&end_date=" + endDate +
      "&station=" + String(tideStation) +
      "&product=predictions"
      "&datum=" + String(tideDatum) +
      "&time_zone=lst_ldt"
      "&units=english"
      "&interval=hilo"
      "&format=json";

  JsonDocument doc;

  if (!fetchNOAAJson(url, doc)) {
    return false;
  }

  if (doc["predictions"].isNull()) {
    Serial.println("No high/low predictions returned");
    return false;
  }

  time_t now = time(nullptr);
  time_t previousTime = 0;
  time_t nextTime = 0;
  time_t highTime = 0;
  time_t lowTime = 0;

  tide.previousEvent.valid = false;
  tide.nextEvent.valid = false;
  tide.nextHigh.valid = false;
  tide.nextLow.valid = false;
  tide.valid = false;

  for (JsonObject p : doc["predictions"].as<JsonArray>()) {
    const char *timeText = p["t"] | "";
    const char *type = p["type"] | "";
    float height = String(p["v"] | "0").toFloat();

    time_t eventTime;

    if (!parseTideTime(timeText, eventTime)) {
      continue;
    }

    // Save the latest high/low event at or before now.
    if (eventTime <= now && eventTime > previousTime) {
      previousTime = eventTime;
      tide.previousEvent.time = String(timeText);
      tide.previousEvent.type = String(type);
      tide.previousEvent.height = height;
      tide.previousEvent.valid = true;
    }

    // Save the earliest high/low event after now.
    if (eventTime > now &&
        (nextTime == 0 || eventTime < nextTime)) {
      nextTime = eventTime;
      tide.nextEvent.time = String(timeText);
      tide.nextEvent.type = String(type);
      tide.nextEvent.height = height;
      tide.nextEvent.valid = true;
    }

    // Find the next high tide.
    if (eventTime > now &&
        strcmp(type, "H") == 0 &&
        (highTime == 0 || eventTime < highTime)) {
      highTime = eventTime;
      tide.nextHigh.time = String(timeText);
      tide.nextHigh.type = "H";
      tide.nextHigh.height = height;
      tide.nextHigh.valid = true;
    }

    // Find the next low tide.
    if (eventTime > now &&
        strcmp(type, "L") == 0 &&
        (lowTime == 0 || eventTime < lowTime)) {
      lowTime = eventTime;
      tide.nextLow.time = String(timeText);
      tide.nextLow.type = "L";
      tide.nextLow.height = height;
      tide.nextLow.valid = true;
    }
  }

  if (!tide.previousEvent.valid || !tide.nextEvent.valid) {
    Serial.println("Missing tide events surrounding current time");
    return false;
  }

  time_t t1, t2;

  if (!parseTideTime(tide.previousEvent.time.c_str(), t1) ||
      !parseTideTime(tide.nextEvent.time.c_str(), t2) ||
      t2 <= t1) {
    Serial.println("Invalid tide event times");
    return false;
  }

  // Fraction of the time elapsed between the two events.
  float fraction =
      (float)(now - t1) / (float)(t2 - t1);

  fraction = constrain(fraction, 0.0f, 1.0f);

  float h1 = tide.previousEvent.height;
  float h2 = tide.nextEvent.height;

  // Cosine interpolation between consecutive high/low tides.
  const float PI_F = 3.14159265f;

  tide.height =
      (h1 + h2) / 2.0f +
      (h1 - h2) / 2.0f * cosf(PI_F * fraction);

  if (h2 > h1) {
    tide.direction = "Rising";
  } else if (h2 < h1) {
    tide.direction = "Falling";
  } else {
    tide.direction = "Near steady";
  }

  tide.valid = true;

  Serial.printf("Estimated tide: %.2f ft, %s\n",
                tide.height, tide.direction.c_str());

  Serial.printf("Previous event: %s, %.2f ft\n",
                tide.previousEvent.time.c_str(), h1);

  Serial.printf("Next event: %s, %.2f ft\n",
                tide.nextEvent.time.c_str(), h2);

  return true;
}

/* --------------------- UPDATE TIDE DATA ------------------------ */

bool fetchTide() {
  connectWiFi();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Tide update skipped: no Wi-Fi");
    return false;
  }

  if (!clockReady) {
    initClock();
  }

  if (!clockReady) {
    Serial.println("Tide update skipped: clock unavailable");
    return false;
  }

  bool ok = fetchHighLowTides();

  Serial.printf("High tide: %s\n",
      tide.nextHigh.valid
          ? tide.nextHigh.time.c_str() : "Unavailable");

  Serial.printf("Low tide: %s\n",
      tide.nextLow.valid
          ? tide.nextLow.time.c_str() : "Unavailable");

  return ok;
}

bool fetchNWSJson(const String &url,
                  DynamicJsonDocument &doc) {
  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.setTimeout(20000);

  Serial.println("NWS request URL:");
  Serial.println(url);

  if (!http.begin(client, url)) {
    Serial.println("NWS: Could not start request");
    return false;
  }

  http.addHeader(
      "User-Agent",
      "PaperDIYWeatherMonitor/1.0 (your-email@example.com)"
  );
  http.addHeader("Accept", "application/geo+json");

  int code = http.GET();

  Serial.printf("NWS HTTP status: %d\n", code);
  Serial.printf("Content-Type: %s\n",
                http.header("Content-Type").c_str());

  if (code != HTTP_CODE_OK) {
    Serial.println("NWS response:");
    Serial.println(http.getString().substring(0, 500));
    http.end();
    return false;
  }

  // Read the body once, so we can inspect it if parsing fails.
  String body = http.getString();
  http.end();

  DeserializationError err = deserializeJson(doc, body);

  if (err) {
    Serial.printf("NWS JSON parse error: %s\n", err.c_str());
    Serial.println("Response body (first 500 characters):");
    Serial.println(body.substring(0, 500));
    return false;
  }

  // Detect an API error returned as JSON.
  if (!doc["status"].isNull() &&
      doc["status"].as<int>() >= 400) {
    Serial.println("NWS API error:");
    serializeJson(doc, Serial);
    Serial.println();
    return false;
  }

  return true;
}

/* --------------------- WEATHER FETCH --------------------------- */

bool fetchWeather() {
  connectWiFi();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("NWS: No Wi-Fi");
    return false;
  }

  // Request 1: Resolve coordinates to NWS forecast URLs.
  String pointsUrl =
      "https://api.weather.gov/points/" +
      String(lat, 4) + "," + String(lon, 4);

  DynamicJsonDocument pointsDoc(12000);

  if (!fetchNWSJson(pointsUrl, pointsDoc)) {
    Serial.println("NWS: Point lookup failed");
    return false;
  }

  String hourlyUrl =
      pointsDoc["properties"]["forecastHourly"] | "";

  String gridUrl =
      pointsDoc["properties"]["forecastGridData"] | "";

  weather.city =
      pointsDoc["properties"]["relativeLocation"]
              ["properties"]["city"] | "Local Forecast";

  if (hourlyUrl.length() == 0) {
    Serial.println("NWS: Hourly forecast URL missing");
    return false;
  }

  // Request 2: Get the hourly forecast.
  DynamicJsonDocument forecastDoc(24000);

  if (!fetchNWSJson(hourlyUrl, forecastDoc)) {
    Serial.println("NWS: Hourly forecast failed");
    return false;
  }

  JsonArray periods =
      forecastDoc["properties"]["periods"].as<JsonArray>();

  if (periods.isNull() || periods.size() == 0) {
    Serial.println("NWS: No hourly forecast periods");
    return false;
  }

  JsonObject period = periods[0];

  // NWS hourly temperature is normally reported in Fahrenheit.
  float temperature =
      period["temperature"] | 0.0f;

  String temperatureUnit =
      period["temperatureUnit"] | "F";

  if (temperatureUnit == "F") {
    weather.tempC = (temperature - 32.0f) * 5.0f / 9.0f;
  } else {
    weather.tempC = temperature;
  }

  weather.description =
      period["shortForecast"] | "Unknown";

  weather.humidity =
      period["relativeHumidity"]["value"] | 0;

  // Request 3: Get raw forecast-grid cloud cover.
  weather.cloudCover = -1;

  if (gridUrl.length() > 0) {
    DynamicJsonDocument gridDoc(60000);

    if (fetchNWSJson(gridUrl, gridDoc)) {
      JsonArray values =
          gridDoc["properties"]["skyCover"]["values"]
                 .as<JsonArray>();

      if (!values.isNull() && values.size() > 0) {
        // Use the first available forecast-grid value.
        for (JsonObject item : values) {
          if (!item["value"].isNull()) {
            weather.cloudCover = item["value"].as<int>();
            break;
          }
        }
      }
    } else {
      Serial.println("NWS: Cloud-cover data unavailable");
    }
  }

  Serial.println("----- NOAA WEATHER -----");
  Serial.printf("Location: %s\n", weather.city.c_str());
  Serial.printf("Forecast: %s\n", weather.description.c_str());
  Serial.printf("Temperature: %.1f C\n", weather.tempC);
  Serial.printf("Humidity: %d%%\n", weather.humidity);

  if (weather.cloudCover >= 0) {
    Serial.printf("Forecast cloud cover: %d%%\n",
                  weather.cloudCover);
  } else {
    Serial.println("Forecast cloud cover unavailable");
  }

  Serial.println("------------------------");

  return true;
}

void fetchSunMoonRiseSet()
{
  // Build the URL – note: we ask for Pacific time
  String url = "http://api.open-meteo.com/v1/forecast";
  url += "?latitude=" + String(lat, 4);
  url += "&longitude=" + String(lon, 4);
  url += "&daily=sunrise,sunset,moonrise,moonset";
  url += "&timezone=America/Los_Angeles";

  HTTPClient http;
  http.begin(url);                         // start connection
  int httpCode = http.GET();               // send the request

  if (httpCode != HTTP_CODE_OK) {
    Serial.printf("HTTP error %d\n", httpCode);
    http.end();
    return;
  }

  // ---- Parse the JSON payload ------------------------------------------
  String payload = http.getString();
  http.end();

  // The response is tiny – a capacity of 2 KB is more than enough
  DynamicJsonDocument doc(2048);
  DeserializationError err = deserializeJson(doc, payload);

  if (err) {
    Serial.printf("JSON parse failed: %s\n", err.c_str());
    return;
  }

  // The JSON structure:
  // { "daily": { "sunrise":[...], "sunset":[...], ... } }
  JsonObject daily = doc["daily"];

  // -----------------------------------------------------------------------
  // Collect the events we found
  // -----------------------------------------------------------------------
  const char *names[] = {"sunrise", "sunset", "moonrise", "moonset"};
  // AstroEvent events[4];
  // int evCount = 0;

  for (int i = 0; i < 4; ++i) {
    const char *key   = names[i];
    JsonArray arr     = daily[key];

    if (!arr || arr.isNull() || arr.size() == 0)
      continue;

    String ts = arr[0];               // e.g. "2026-10-31T07:25"
    int hh = ts.substring(11, 13).toInt();   // characters 11‑12
    int mm = ts.substring(14, 16).toInt();   // characters 14‑15

    String hhStr = (hh < 10) ? "0" + String(hh) : String(hh);
    String mmStr = (mm < 10) ? "0" + String(mm) : String(mm);
    String timeStr = hhStr + ":" + mmStr;

    events[evCount].name   = key;
    events[evCount].time   = timeStr;
    events[evCount].hour   = hh;
    events[evCount].minute = mm;
    evCount++;

    Serial.print(events[evCount].name);
    Serial.print(events[evCount].time);
    Serial.print(events[evCount].hour);
    Serial.print(events[evCount].minute);
    Serial.print(evCount);
  }

  // -----------------------------------------------------------------------
  // Sort the events by clock‑time (hour → minute)
  // -----------------------------------------------------------------------
  for (int i = 0; i < evCount - 1; ++i) {
    for (int j = i + 1; j < evCount; ++j) {
      bool earlier =
          (events[j].hour   < events[i].hour) ||
          (events[j].hour == events[i].hour &&
           events[j].minute < events[i].minute);
      if (earlier) {
        AstroEvent tmp = events[i];
        events[i] = events[j];
        events[j] = tmp;
      }
    }
  }
}
/* --------------------- STOCK FETCH ----------------------- */

// Alpaca latest quote endpoint.
// Free Basic accounts use the IEX feed.
// Displayed price = midpoint between bid and ask.

bool fetchStock() {
  connectWiFi();

  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClientSecure client;
  client.setInsecure(); // TLS encryption without certificate validation

  HTTPClient http;

  String url =
      "https://data.alpaca.markets/v2/stocks/";

  url += stockSymbol;
  url += "/quotes/latest?feed=iex";

  if (!http.begin(client, url)) return false;

  http.addHeader("APCA-API-KEY-ID", alpacaKey);
  http.addHeader("APCA-API-SECRET-KEY", alpacaSecret);
  http.addHeader("Accept", "application/json");

  int httpCode = http.GET();

  if (httpCode != HTTP_CODE_OK) {
    Serial.printf("Stock HTTP error: %d\n", httpCode);

    // Keep the previous quote if the request fails.
    http.end();
    return false;
  }

  JsonDocument doc;

  DeserializationError err =
      deserializeJson(doc, http.getStream());

  if (err) {
    Serial.printf("Stock JSON error: %s\n", err.c_str());
    http.end();
    return false;
  }

  JsonObject quote = doc["quote"];
  if (!quote) {
      Serial.println("JSON missing 'quote' object");
      return false;
  }

  float bid = doc["quote"]["bp"] | 0.0f;
  float ask = doc["quote"]["ap"] | 0.0f;
  float ltp = doc["quote"]["ltp"] | 0.0f;      // latest trade price

  String timestamp = doc["quote"]["t"] | "";

  Serial.printf("Bid: $%.2f", (float) bid);
  Serial.printf("Ask: $%.2f", (float) ask);
  Serial.printf("Last price: $%.2f", (float) ltp);
  // Serial.printf("Ticket: " + stockSymbol);
  http.end();

  if (ltp <= 0.0f) {
     ltp = lastNonZeroQuote;
     stock.price = lastNonZeroQuote; 
  }

  stock.price = (bid + ask) / 2.0f;
  // stock.bid = bid;
  // stock.ask = ask;
  stock.timestamp = timestamp;
  stock.valid = true;

  Serial.printf("Midpoint: $%.2f\n", stock.price);

  return true;
}

/* --------------------- TEMPERATURE ----------------------------- */

float celsiusToFahrenheit(float c) {
  return c * 9.0f / 5.0f + 32.0f;
}

void drawTemperature(float temperature, char unit, int x, int y) {
  auto &d = M5.Display;

  d.setCursor(x, y);
  d.printf("%.1f", temperature);

  int endX = d.getCursorX();

  const int radius = 4;
  const int gap = 3;
  const int circleX = endX + gap + radius;
  const int circleY = y + 7;

  d.drawCircle(circleX, circleY, radius, TFT_BLACK);
  d.setCursor(circleX + radius + gap, y);
  d.print(unit);
}

/* --------------------- OUTLINE WEATHER ICONS ------------------- */

void drawSun(int x, int y, int r) {
  auto &d = M5.Display;
  d.drawCircle(x, y, r, TFT_BLACK);

  for (int angle = 0; angle < 360; angle += 45) {
    float a = angle * PI / 180.0f;

    int x1 = x + cosf(a) * (r + 4);
    int y1 = y + sinf(a) * (r + 4);
    int x2 = x + cosf(a) * (r + 10);
    int y2 = y + sinf(a) * (r + 10);

    d.drawLine(x1, y1, x2, y2, TFT_BLACK);
  }
}

// Cloud outline drawn with overlapping circles and a base.
// Suitable for small monochrome weather illustrations.
void drawCloud(int x, int y, int s) {
  auto &d = M5.Display;

  int r = s / 4;

  d.drawCircle(x - s / 4, y, r, TFT_BLACK);
  d.drawCircle(x, y - s / 6, r + 3, TFT_BLACK);
  d.drawCircle(x + s / 4, y, r, TFT_BLACK);

  // Cover the lower overlapping circle outlines with white.
  d.fillRect(x - s / 2 + 2, y, s - 4, s / 4, TFT_WHITE);

  // Redraw the bottom and sides.
  d.drawLine(x - s / 2 + 2, y, x - s / 2 + 2,
             y + s / 4, TFT_BLACK);
  d.drawLine(x - s / 2 + 2, y + s / 4,
             x + s / 2 - 2, y + s / 4, TFT_BLACK);
  d.drawLine(x + s / 2 - 2, y + s / 4,
             x + s / 2 - 2, y, TFT_BLACK);

  // Restore the top of the cloud after the white mask.
  d.drawArc(x - s / 4, y, r, r, 180, 270, TFT_BLACK);
  d.drawArc(x, y - s / 6, r + 3, r + 3,
            210, 330, TFT_BLACK);
  d.drawArc(x + s / 4, y, r, r, 270, 360, TFT_BLACK);
}

void drawWeatherIcon(int x, int y) {
  String desc = weather.description;
  desc.toLowerCase();
  Serial.println(desc);

  if (desc.indexOf("thunder") >= 0) {
    drawCloud(x, y, 48);
    dummY_unused:
    M5.Display.drawLine(x, y + 12, x - 7, y + 25, TFT_BLACK);
    M5.Display.drawLine(x - 7, y + 25, x + 1, y + 25, TFT_BLACK);
    M5.Display.drawLine(x + 1, y + 25, x - 3, y + 36, TFT_BLACK);
  } else if (desc.indexOf("rain") >= 0 ||
             desc.indexOf("drizzle") >= 0) {
    drawCloud(x, y, 48);
    for (int i = -1; i <= 1; i++) {
      M5.Display.drawLine(x + i * 13, y + 16,
                          x + i * 13 - 5, y + 28, TFT_BLACK);
    }
  } else if (desc.indexOf("snow") >= 0) {
    drawCloud(x, y, 48);
    for (int i = -1; i <= 1; i++) {
      int sx = x + i * 13;
      int sy = y + 25;
      M5.Display.drawLine(sx - 4, sy, sx + 4, sy, TFT_BLACK);
      M5.Display.drawLine(sx, sy - 4, sx, sy + 4, TFT_BLACK);
      M5.Display.drawLine(sx - 3, sy - 3, sx + 3, sy + 3, TFT_BLACK);
    }
  } else if (desc.indexOf("cloud") >= 0 ||
             desc.indexOf("overcast") >= 0 ||
             desc.indexOf("mist") >= 0 ||
             desc.indexOf("fog") >= 0) {
    drawCloud(x, y, 48);
    if (desc.indexOf("fog") >= 0 ||
        desc.indexOf("mist") >= 0) {
      for (int i = 0; i < 3; i++) {
        M5.Display.drawLine(x - 24, y + 27 + i * 7,
                            x + 24, y + 27 + i * 7, TFT_BLACK);
      }
    }
  } else if (desc.indexOf("clear") >= 0 || 
            desc.indexOf("sunny") >= 0)  {
    drawSun(x, y, 16);
  } else {
    drawSun(x - 16, y - 10, 12);
    drawCloud(x + 7, y + 9, 40);
  }
}

/* --------------------- MOON PHASE ------------------------------ */

// Approximate phase from 0.0 to 1.0.
// 0 = New Moon, 0.5 = Full Moon.
float getMoonPhase() {
  time_t now = time(nullptr);

  if (now < 1000000000) return -1.0f;

  const double newMoonEpoch = 947182440.0;
  const double lunarCycle = 29.530588853 * 86400.0;

  double phase = fmod(
      (double)now - newMoonEpoch, lunarCycle) / lunarCycle;

  if (phase < 0) phase += 1.0;

  return (float)phase;
}

const char* getMoonPhaseName(float p) {
  if (p < 0)       return "Time unavailable";
  if (p < 0.0625f || p >= 0.9375f) return "New Moon";
  if (p < 0.1875f) return "Waxing Crescent";
  if (p < 0.3125f) return "First Quarter";
  if (p < 0.4375f) return "Waxing Gibbous";
  if (p < 0.5625f) return "Full Moon";
  if (p < 0.6875f) return "Waning Gibbous";
  if (p < 0.8125f) return "Last Quarter";
  return "Waning Crescent";
}

// White disk, black shadow, and outline.
// Waxing phases have the illuminated area growing on the right.
void drawMoon(int x, int y, int r, float phase) {
  auto &d = M5.Display;

  if (phase < 0) {
    d.drawCircle(x, y, r, TFT_BLACK);
    return;
  }

  // White lunar disk
  d.fillCircle(x, y, r, TFT_WHITE);

  // Approximate the terminator with scanlines.
  float c = cosf(2.0f * PI * phase);

  for (int dy = -r; dy <= r; dy++) {
    float q = 1.0f - ((float)dy * dy) / ((float)r * r);
    if (q <= 0) continue;

    int w = (int)(r * sqrtf(q));
    int boundary = (int)(c * w);

    if (phase < 0.5f) {
      // Waxing: shadow on the left, lit area on the right.
      boundary = constrain(boundary, -w, w);
      if (boundary > -w) {
        d.drawLine(x - w, y + dy, x + boundary, y + dy,
                   TFT_BLACK);
      }
    } else {
      // Waning: shadow on the right, lit area on the left.
      boundary = constrain(-boundary, -w, w);
      if (boundary < w) {
        d.drawLine(x + boundary, y + dy, x + w, y + dy,
                   TFT_BLACK);
      }
    }
  }

  // Craters and outline
  d.drawCircle(x - r / 3, y - r / 4, 3, TFT_BLACK);
  d.drawCircle(x + r / 4, y + r / 3, 2, TFT_BLACK);
  d.drawCircle(x, y, r, TFT_BLACK);
}

float getMoonIllumination(float phase) {
  if (phase < 0) return -1.0f;
  return (1.0f - cosf(2.0f * PI * phase)) * 50.0f;
}

void drawMoonSection(int x, int y) {
  auto &d = M5.Display;
  float phase = getMoonPhase();

  drawMoon(x, y + 22, 22, phase);

  d.setTextSize(2);
  d.setCursor(x + 34, y);
  d.print(getMoonPhaseName(phase));

  d.setCursor(x + 34, y + 25);

  float illumination = getMoonIllumination(phase);

  if (illumination >= 0) {
    d.printf("%.0f%% illuminated", illumination);
  } else {
    d.print("Waiting for time");
  }
}

// Calculate week of year
int getISOWeekNumber(int year, int month, int day) {
  // Calculate day of the year
  int daysInMonth[] = {
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 31
  };

  // Check for leap year
  bool leapYear = (year % 4 == 0 && year % 100 != 0) ||
                  (year % 400 == 0);

  if (leapYear) {
    daysInMonth[1] = 29;
  }

  int dayOfYear = day;

  for (int i = 0; i < month - 1; i++) {
    dayOfYear += daysInMonth[i];
  }

  // Calculate weekday (0 = Sunday, 1 = Monday, etc.)
  int y = year;
  int m = month;

  if (m < 3) {
    m += 12;
    y--;
  }

  int k = y % 100;
  int j = y / 100;

  int h = (day + (13 * (m + 1)) / 5 +
           k + k / 4 + j / 4 + 5 * j) % 7;

  int weekday = (h + 6) % 7; // Sunday = 0

  // Convert to ISO weekday (Monday = 1, Sunday = 7)
  int isoWeekday = weekday == 0 ? 7 : weekday;

  // Calculate ISO week number
  int week = (dayOfYear - isoWeekday + 10) / 7;
  Serial.printf("Week=%d",week);

  if (week < 1) {
    return getISOWeekNumber(year - 1, 12, 31);
  }

  // Determine whether this year has 52 or 53 ISO weeks
  int jan1Weekday = (weekday - ((dayOfYear - 1) % 7) + 7) % 7;
  int weeksInYear = (jan1Weekday == 4 ||
                     (jan1Weekday == 3 && leapYear)) ? 53 : 52;

  if (week > weeksInYear) {
    return 1;
  }

  return week;
}

// Calculate day of year
int getDayOfYear(int year, int month, int day) {

  int daysInMonth[] = {
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 31
  };

  // Check for leap year
  bool leapYear = (year % 4 == 0 && year % 100 != 0) ||
                  (year % 400 == 0);

  if (leapYear) {
    daysInMonth[1] = 29;
  }

  int dayOfYear = day;

  for (int i = 0; i < month - 1; i++) {
    dayOfYear += daysInMonth[i];
  }
  Serial.printf("Day=%d", dayOfYear);

  return dayOfYear;
}


/* --------------------- DISPLAY --------------------------------- */

void drawScreen() {
  auto &d = M5.Display;

  int screenW = d.width();
  int screenH = d.height();
  
  d.fillScreen(TFT_WHITE);
  d.setTextColor(TFT_BLACK);
  d.setFont(nullptr);

  // Header
  d.setTextSize(2);
  d.setCursor(25, 14);
  d.print(weather.city);

  setenv("TZ", "PST8PDT,M3.2.0,M11.1.0", 1);
  tzset();

  time_t now = time(nullptr);
  struct tm t;
  localtime_r(&now, &t);

  Serial.printf("Year %d Month %02d Day %02d  Time %02d:%02d:%02d\n",
              t.tm_year + 1900, t.tm_mon+1, t.tm_mday,
              t.tm_hour, t.tm_min, t.tm_sec);

  d.setTextSize(2);
  d.setCursor(200, 14);
  d.print(formatDate());

  int weekOfYear = getISOWeekNumber(t.tm_year + 1900, t.tm_mon+1, t.tm_mday);
  int dayOfYear = getDayOfYear(t.tm_year + 1900, t.tm_mon+1, t.tm_mday);
  Serial.printf("week=%d", weekOfYear);
  Serial.printf("day=%d", dayOfYear);

  d.setCursor(d.width() - 95, 14);
  d.printf("%02d:%02d", t.tm_hour, t.tm_min);

  d.drawLine(8, 35, d.width() - 8, 35, TFT_BLACK);

  // Temperature
  d.setTextSize(3);
  drawTemperature(weather.tempC, 'C', 25, 48);
  drawTemperature(celsiusToFahrenheit(weather.tempC), 'F', 25, 88);

  d.setCursor(200, 48);
  d.printf("Week %2d", weekOfYear);
  d.setCursor(200, 88);
  d.printf("Day %3d", dayOfYear);

  // Weather icon and description
  drawWeatherIcon(d.width() - 65, 85);

  d.setTextSize(2);
  d.setCursor(25, 132);
  d.print(weather.description);

  d.setCursor(25, 158);
  d.printf("Humidity: %d%%", weather.humidity);

  d.drawLine(8, 190, d.width() - 8, 190, TFT_BLACK);

  // Battery
  d.setCursor(25, 202);

  if (batteryReadOK) {
    d.printf("Battery: %.2f V", batteryVoltage);
    d.setCursor(25, 228);
    d.printf("Charge: %d%%", batteryPercent);
  } else {
    d.print("Battery unavailable");
  }

  d.drawLine(8, 260, d.width() - 8, 260, TFT_BLACK);

  d.setCursor(220, 202);
  d.printf("Latitude: %f", lat);
  d.setCursor(220, 228);
  d.printf("Longitude: %f", lon);

  int yMargin = 270;

  // Serial.printf("evCount=%s", evCount);
  // evCount = 4;

  for (int i = 0; i < evCount; ++i) {
    Serial.printf("%s : %s\n", events[i].name, events[i].time.c_str());
    d.setCursor(285, yMargin+20*i);
    d.printf("%s : %s\n", events[i].name, events[i].time.c_str());
  }

  // Moon phase
  d.setCursor(25, 270);
  d.print("Moon Phase");

  drawMoonSection(38, 302);

  d.drawLine(8, 360, d.width() - 8, 360, TFT_BLACK);

  // Stock

  d.setCursor(25, 375);
  d.print("Ticket=");

  if (stock.valid) {
    d.setCursor(25, 400);
    d.printf("Price: $%.2f", stock.price);
  }

  d.drawLine(8, 480, d.width() - 8, 480, TFT_BLACK);

  // Tide info
  // Dynamic vertical layout works on different screen sizes.
  int margin = 25;
  int y = 500;

  d.setTextSize(3);
  d.setCursor(margin, y);
  d.print("Location");

  y += 34;

  d.setTextSize(2);
  d.setCursor(margin, y);
  d.print("TIDE MONITOR");

  y += 34;

  d.drawLine(8, y, screenW - 8, y, INK);
  y += 18;

  if (tide.valid) {
    d.setTextSize(2);
    d.setCursor(margin, y);
    d.print("PREDICTED HEIGHT");

    y += 30;

    d.setTextSize(3);
    d.setCursor(margin, y);
    d.printf("%.2f ft", tide.height);

    y += 48;

    d.setTextSize(3);
    d.setCursor(margin, y);
    d.print(tide.direction);

    y += 40;
  } else {
    d.setTextSize(2);
    d.setCursor(margin, y);
    d.print("Tide height unavailable");

    y += 36;
  }

  d.drawLine(8, y, screenW - 8, y, INK);
  y += 16;

  d.setTextSize(2);
  d.setCursor(margin, y);
  d.print("NEXT HIGH TIDE");

  y += 30;

  if (tide.nextHigh.valid) {
    d.setTextSize(3);
    d.setCursor(margin, y);
    d.printf("%.2f ft", tide.nextHigh.height);

    y += 34;

    d.setTextSize(2);
    d.setCursor(margin, y);
    d.print(formatTideTime(tide.nextHigh.time));
  } else {
    d.setTextSize(2);
    d.setCursor(margin, y);
    d.print("Unavailable");
  }

  y += 38;

  d.drawLine(8, y, screenW - 8, y, INK);
  y += 16;

  d.setTextSize(2);
  d.setCursor(margin, y);
  d.print("NEXT LOW TIDE");

  y += 30;

  if (tide.nextLow.valid) {
    d.setTextSize(3);
    d.setCursor(margin, y);
    d.printf("%.2f ft", tide.nextLow.height);

    y += 34;

    d.setTextSize(2);
    d.setCursor(margin, y);
    d.print(formatTideTime(tide.nextLow.time));
  } else {
    d.setTextSize(2);
    d.setCursor(margin, y);
    d.print("Unavailable");
  }

  // Footer, only if it fits on this display.
  if (y + 32 < screenH - 8) {
    d.setTextSize(1);
    d.setCursor(margin, screenH - 25);
    d.print("NOAA station 9413745");
  }

  // Rectangle border
  d.drawRect(8, 8, d.width() - 16, d.height() - 16, TFT_BLACK);

  d.setEpdMode(epd_mode_t::epd_quality);
  d.display();
}

/* --------------------- SETUP ----------------------------------- */

void setup() {
  Serial.begin(115200);
  delay(1000);

  // *** NEW: set the time zone early ***
  initClock();            // sets TZ to PST8PDT and synchronises NTP
  if (!clockReady) {
    Serial.println("Failed to sync clock – falling back to UTC");
  }

  auto cfg = M5.config();
  M5.begin(cfg);
  M5.Display.setRotation(0);

  // Initialize onboard M5PM1 power manager.
  m5pm1_err_t err =
      pm1.begin(&M5.In_I2C,
                M5PM1_DEFAULT_ADDR,
                M5PM1_I2C_FREQ_100K);

  pm1Ready = (err == M5PM1_OK);

  if (!pm1Ready) {
    Serial.printf("M5PM1 initialization failed: %d\n", (int)err);
  }

  connectWiFi();

  // Synchronize clock for moon phase calculations.
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");

  struct tm timeInfo;
  if (getLocalTime(&timeInfo, 10000)) {
    Serial.println("Clock synchronized.");
  } else {
    Serial.println("Clock not synchronized yet.");
  }

  readBattery();

  bool weatherOK = fetchWeather();
  bool stockOK = fetchStock();
  fetchTide();
  fetchSunMoonRiseSet();

  // Display whichever data is available.
  if (weatherOK || stockOK) {
    drawScreen();
  }

  lastFetch = millis();
}

/* --------------------- LOOP ------------------------------------ */

void loop() {
  M5.update();

  unsigned long now = millis();

  if (now - lastFetch >= fetchInterval) {
    lastFetch = now;

    bool weatherOK = fetchWeather();
    bool stockOK = fetchStock();
    fetchTide();
    fetchSunMoonRiseSet();

    readBattery();

    if (weatherOK || stockOK) {
      drawScreen();
    }
  }

  delay(20);
}
