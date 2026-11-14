#include <M5Unified.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==================================================
// WIFI SETTINGS
// ==================================================

const char* ssid = "SSID";
const char* password = "WiFi_Pass";

// ==================================================
// WEATHER LOCATION
// ==================================================

const float latitude  = 40.9872;
const float longitude = -90.9348;

// ==================================================
// REFRESH INTERVAL
// ==================================================

const unsigned long UPDATE_INTERVAL = 1800000UL;

unsigned long lastUpdate = 0;

// ==================================================
// WEATHER DATA STRUCTURE
// ==================================================

struct DailyForecast {
  String date;
  int high;
  int low;
  String conditions;
  String wind;
  int rainChance;
};

DailyForecast dailyForecast[5];

int dayCount = 0;

// ==================================================
// DISPLAY CANVAS
// ==================================================

M5Canvas canvas(&M5.Display);

// ==================================================
// WEATHER ICON TYPES
// ==================================================

enum WeatherIcon {
  ICON_SUN,
  ICON_PARTLY,
  ICON_CLOUD,
  ICON_RAIN,
  ICON_SNOW,
  ICON_UNKNOWN
};

// ==================================================
// WIFI CONNECTION
// ==================================================

void connectWiFi() {

  Serial.println("Connecting to WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected!");

}

// ==================================================
// HTTPS JSON REQUEST
// ==================================================

bool fetchJSON(
  const String& url,
  JsonDocument& doc
) {

  WiFiClientSecure client;

  // Initial testing only.
  // Replace with certificate validation for deployment.
  client.setInsecure();

  HTTPClient http;

  http.setTimeout(20000);

  if (!http.begin(client, url)) {
    Serial.println("HTTP begin failed");
    return false;
  }

  http.addHeader(
    "User-Agent",
    "M5PaperDIYWeatherStation/1.0"
  );

  int httpCode = http.GET();

  if (httpCode != HTTP_CODE_OK) {

    Serial.printf(
      "HTTP request failed: %d\n",
      httpCode
    );

    http.end();
    return false;
  }

  DeserializationError error =
    deserializeJson(doc, http.getStream());

  http.end();

  if (error) {

    Serial.print("JSON error: ");
    Serial.println(error.c_str());

    return false;
  }

  return true;
}

/* --------------------------------------------------------------------
   DRAW FULL CONDITION TEXT – wrapped into one or two lines
-------------------------------------------------------------------- */
void drawWrappedCondition(const String &text,
                          int centerX,          // middle of the column
                          int topY) {           // y‑coordinate for the first line

  const int maxCharsPerLine = 15;          // adjust to your font size / column width
  String first, second;

  if (text.length() <= maxCharsPerLine) {
    // fits in one line – just draw it
    canvas.drawString(text, centerX, topY);

  } else {
    // need to wrap – find the last space that fits in line 1
    int splitPos = maxCharsPerLine;
    while (splitPos > 0 && text[splitPos] != ' ') splitPos--;

    if (splitPos == 0) {            // no space found – force split
      splitPos = maxCharsPerLine;
    }

    first  = text.substring(0, splitPos);

    second = text.substring(splitPos);   // <-- get the rest
    second.trim();                       // remove leading/trailing spaces

    // draw the two lines, 1 line height apart
    canvas.drawString(first,   centerX, topY);
    canvas.drawString(second,  centerX, topY + 20); // 20 px line height
  }
}


// ==================================================
// GET WEATHER FORECAST
// ==================================================

bool getWeatherForecast() {

  Serial.println("Retrieving weather...");

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected");
    return false;
  }

  // ----------------------------------------------
  // STEP 1: GET NWS POINT INFORMATION
  // ----------------------------------------------

  String pointURL =
    "https://api.weather.gov/points/" +
    String(latitude, 4) + "," +
    String(longitude, 4);

  JsonDocument pointDoc;

  if (!fetchJSON(pointURL, pointDoc)) {
    return false;
  }

  String forecastURL =
    pointDoc["properties"]["forecast"].as<String>();

  if (forecastURL.length() == 0) {
    Serial.println("Forecast URL missing");
    return false;
  }

  // ----------------------------------------------
  // STEP 2: GET FORECAST
  // ----------------------------------------------

  JsonDocument forecastDoc;

  if (!fetchJSON(
    forecastURL + "?units=us",
    forecastDoc
  )) {
    return false;
  }

  // ----------------------------------------------
  // STEP 3: EXTRACT FORECAST PERIODS
  // ----------------------------------------------

  JsonArray periods =
    forecastDoc["properties"]["periods"].as<JsonArray>();

  if (periods.isNull()) {
    Serial.println("No forecast periods");
    return false;
  }

  dayCount = 0;

  int periodCount = 0;

  for (JsonObject period : periods) {

    if (periodCount >= 10) {
      break;
    }

    periodCount++;

    String startTime =
      period["startTime"].as<String>();

    String date = startTime.substring(0, 10);

    bool isDaytime = period["isDaytime"] | false;

    // --------------------------------------------
    // FIND EXISTING DATE
    // --------------------------------------------

    int index = -1;

    for (int i = 0; i < dayCount; i++) {

      if (dailyForecast[i].date == date) {
        index = i;
        break;
      }
    }

    // --------------------------------------------
    // CREATE NEW DAY
    // --------------------------------------------

    if (index == -1) {

      if (dayCount >= 5) {
        continue;
      }

      index = dayCount++;

      dailyForecast[index].date = date;
      dailyForecast[index].high = -999;
      dailyForecast[index].low = -999;
      dailyForecast[index].conditions = "";
      dailyForecast[index].wind = "";
      dailyForecast[index].rainChance = -1;
    }

    // --------------------------------------------
    // DAYTIME FORECAST
    // --------------------------------------------

    if (isDaytime) {

      dailyForecast[index].high =
        period["temperature"] | -999;

      dailyForecast[index].conditions =
        period["shortForecast"].as<String>();

      dailyForecast[index].wind =
        period["windSpeed"].as<String>() +
        " " +
        period["windDirection"].as<String>();

      dailyForecast[index].rainChance =
        period["probabilityOfPrecipitation"]["value"] | -1;
    }

    // --------------------------------------------
    // NIGHTTIME FORECAST
    // --------------------------------------------

    else {

      dailyForecast[index].low =
        period["temperature"] | -999;

      // Fallback if daytime forecast isn't available
      if (dailyForecast[index].conditions.length() == 0) {

        dailyForecast[index].conditions =
          period["shortForecast"].as<String>();

        dailyForecast[index].wind =
          period["windSpeed"].as<String>() +
          " " +
          period["windDirection"].as<String>();

        dailyForecast[index].rainChance =
          period["probabilityOfPrecipitation"]["value"] | -1;
      }
    }
  }

  Serial.printf(
    "Retrieved %d forecast days\n",
    dayCount
  );

  return dayCount > 0;
}

// ==================================================
// GET WEEKDAY FROM YYYY-MM-DD
// ==================================================

String getWeekday(String date) {

  int year = date.substring(0, 4).toInt();
  int month = date.substring(5, 7).toInt();
  int day = date.substring(8, 10).toInt();

  if (month < 3) {
    month += 12;
    year--;
  }

  int k = year % 100;
  int j = year / 100;

  int h =
    (day + (13 * (month + 1)) / 5 +
    k + k / 4 + j / 4 + 5 * j) % 7;

  const char* weekdays[] = {
    "SAT", "SUN", "MON", "TUE",
    "WED", "THU", "FRI"
  };

  return weekdays[h];
}

// ==================================================
// DETERMINE WEATHER ICON
// ==================================================

WeatherIcon getWeatherIcon(String conditions) {

  conditions.toLowerCase();

  if (
    conditions.indexOf("snow") >= 0 ||
    conditions.indexOf("sleet") >= 0
  ) {
    return ICON_SNOW;
  }

  if (
    conditions.indexOf("rain") >= 0 ||
    conditions.indexOf("shower") >= 0 ||
    conditions.indexOf("drizzle") >= 0 ||
    conditions.indexOf("storm") >= 0
  ) {
    return ICON_RAIN;
  }

  if (
    conditions.indexOf("partly") >= 0 ||
    conditions.indexOf("mostly sunny") >= 0 ||
    conditions.indexOf("mostly clear") >= 0
  ) {
    return ICON_PARTLY;
  }

  if (
    conditions.indexOf("cloud") >= 0 ||
    conditions.indexOf("overcast") >= 0 ||
    conditions.indexOf("fog") >= 0
  ) {
    return ICON_CLOUD;
  }

  if (
    conditions.indexOf("sun") >= 0 ||
    conditions.indexOf("clear") >= 0
  ) {
    return ICON_SUN;
  }

  return ICON_UNKNOWN;
}

// ==================================================
// DRAW SUN ICON
// ==================================================

void drawSun(int x, int y) {

  canvas.drawCircle(x, y, 15, TFT_BLACK);

  for (int angle = 0; angle < 360; angle += 45) {

    float rad = angle * PI / 180.0;

    int x1 = x + cos(rad) * 21;
    int y1 = y + sin(rad) * 21;

    int x2 = x + cos(rad) * 29;
    int y2 = y + sin(rad) * 29;

    canvas.drawLine(
      x1, y1, x2, y2, TFT_BLACK
    );
  }
}

// ==================================================
// DRAW CLOUD ICON
// ==================================================

void drawCloud(int x, int y) {

  canvas.drawCircle(x - 13, y + 3, 11, TFT_BLACK);
  canvas.drawCircle(x, y - 5, 15, TFT_BLACK);
  canvas.drawCircle(x + 14, y + 4, 10, TFT_BLACK);

  canvas.drawLine(
    x - 23, y + 13,
    x + 23, y + 13,
    TFT_BLACK
  );
}

// ==================================================
// DRAW RAIN ICON
// ==================================================

void drawRain(int x, int y) {

  drawCloud(x, y - 7);

  canvas.drawLine(
    x - 12, y + 19,
    x - 17, y + 29,
    TFT_BLACK
  );

  canvas.drawLine(
    x, y + 19,
    x - 5, y + 29,
    TFT_BLACK
  );

  canvas.drawLine(
    x + 12, y + 19,
    x + 7, y + 29,
    TFT_BLACK
  );
}

// ==================================================
// DRAW SNOW ICON
// ==================================================

void drawSnow(int x, int y) {

  drawCloud(x, y - 7);

  for (int i = -1; i <= 1; i++) {

    int sx = x + i * 13;

    canvas.drawLine(
      sx - 4, y + 23,
      sx + 4, y + 31,
      TFT_BLACK
    );

    canvas.drawLine(
      sx - 4, y + 31,
      sx + 4, y + 23,
      TFT_BLACK
    );
  }
}

// ==================================================
// DRAW WEATHER ICON
// ==================================================

void drawWeatherIcon(
  WeatherIcon icon,
  int x,
  int y
) {

  switch (icon) {

    case ICON_SUN:
      drawSun(x, y);
      break;

    case ICON_PARTLY:
      drawSun(x - 12, y - 7);
      drawCloud(x + 7, y + 8);
      break;

    case ICON_CLOUD:
      drawCloud(x, y);
      break;

    case ICON_RAIN:
      drawRain(x, y);
      break;

    case ICON_SNOW:
      drawSnow(x, y);
      break;

    default:
      canvas.setTextDatum(middle_center);
      canvas.setTextSize(3);
      canvas.drawString("?", x, y);
      break;
  }
}

// ==================================================
// DISPLAY FIVE DAY FORECAST
// ==================================================

void displayForecast() {

  int screenW = M5.Display.width();
  int screenH = M5.Display.height();

  int colW = screenW / 5;

  canvas.fillSprite(TFT_WHITE);

  canvas.setTextColor(TFT_BLACK);

  // ----------------------------------------------
  // HEADER
  // ----------------------------------------------

  canvas.setTextDatum(middle_center);
  canvas.setTextSize(3);

  canvas.drawString(
    "5-DAY WEATHER FORECAST",
    screenW / 2,
    30
  );

  canvas.drawLine(
    10, 62,
    screenW - 10, 62,
    TFT_BLACK
  );

  // ----------------------------------------------
  // FIVE DAILY COLUMNS
  // ----------------------------------------------

  for (int i = 0; i < dayCount; i++) {

    int x = i * colW;
    int centerX = x + colW / 2;

    // Vertical separator
    if (i > 0) {

      canvas.drawLine(
        x, 72,
        x, screenH - 12,
        TFT_BLACK
      );
    }

    // WEEKDAY
    canvas.setTextSize(2);

    canvas.drawString(
      getWeekday(dailyForecast[i].date),
      centerX,
      88
    );

    // DATE
    String dateText =
      dailyForecast[i].date.substring(5, 10);

    canvas.setTextSize(2);

    canvas.drawString(
      dateText.c_str(),
      centerX,
      112
    );

    // WEATHER ICON
    WeatherIcon icon =
      getWeatherIcon(dailyForecast[i].conditions);

    drawWeatherIcon(
      icon,
      centerX,
      165
    );

    // CONDITIONS – use wrapped string helper
    canvas.setTextSize(2);          // keep the same size you used before

    String conditions = dailyForecast[i].conditions;

    // Keep long descriptions from overflowing
    if (conditions.length() > 30) {
      conditions = conditions.substring(0, 30) + "...";
    }

    // *** NEW CODE ***
    drawWrappedCondition(conditions, centerX, 218);

    // HIGH TEMPERATURE
    canvas.setTextSize(3);

    String highText =
      dailyForecast[i].high == -999
      ? "--"
      : String(dailyForecast[i].high) + "F";

    canvas.drawString(
      highText.c_str(),
      centerX,
      275
    );

    // LOW TEMPERATURE
    canvas.setTextSize(2);

    String lowText =
      dailyForecast[i].low == -999
      ? "--"
      : String(dailyForecast[i].low) + "F";

    canvas.drawString(
      lowText.c_str(),
      centerX,
      318
    );

    canvas.drawLine(
      x + 15, 345,
      x + colW - 15, 345,
      TFT_BLACK
    );

    // WIND LABEL
    canvas.setTextSize(2);

    canvas.drawString(
      "WIND",
      centerX,
      370
    );

    // WIND VALUE
    String windText =
      dailyForecast[i].wind;

    if (windText.length() > 22) {
      windText = windText.substring(0, 21);
    }

    canvas.drawString(
      windText.c_str(),
      centerX,
      393
    );

    // RAIN LABEL
    canvas.drawString(
      "RAIN CHANCE",
      centerX,
      435
    );

    // RAIN VALUE
    canvas.setTextSize(2);

    String rainText =
      dailyForecast[i].rainChance >= 0
      ? String(dailyForecast[i].rainChance) + "%"
      : "N/A";

    canvas.drawString(
      rainText.c_str(),
      centerX,
      470
    );
  }

  // ----------------------------------------------
  // PUSH TO E-PAPER DISPLAY
  // ----------------------------------------------

  canvas.pushSprite(0, 0);

  Serial.println("Display updated");
}

// ==================================================
// SETUP
// ==================================================

void setup() {

  Serial.begin(115200);

  auto cfg = M5.config();

  M5.begin(cfg);

  M5.Display.setRotation(1);

  // Create full-screen drawing canvas
  if (!canvas.createSprite(
    M5.Display.width(),
    M5.Display.height()
  )) {

    Serial.println("Canvas allocation failed!");
    return;
  }

  canvas.setTextColor(TFT_BLACK);

  canvas.fillSprite(TFT_WHITE);
  canvas.setTextDatum(middle_center);
  canvas.setTextSize(2);

  canvas.drawString(
    "Starting Weather Station...",
    M5.Display.width() / 2,
    M5.Display.height() / 2
  );

  canvas.pushSprite(0, 0);

  connectWiFi();

  if (getWeatherForecast()) {
    displayForecast();
  }

  lastUpdate = millis();
}

// ==================================================
// LOOP
// ==================================================

void loop() {

  M5.update();

  // Refresh forecast every 30 minutes
  if (
    millis() - lastUpdate >= UPDATE_INTERVAL
  ) {

    lastUpdate = millis();

    if (WiFi.status() != WL_CONNECTED) {
      connectWiFi();
    }

    if (getWeatherForecast()) {
      displayForecast();
    }
  }

  delay(100);
}