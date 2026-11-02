#include <Arduino.h>
#include <M5Unified.h>

M5Canvas canvas(&M5.Display);

void setup()
{
    auto cfg = M5.config();
    cfg.clear_display = false;

    M5.begin(cfg);

    M5.Display.setEpdMode(epd_mode_t::epd_quality);

    canvas.createSprite(
        M5.Display.width(),
        M5.Display.height()
    );

    canvas.fillSprite(TFT_WHITE);

    canvas.setTextColor(TFT_BLACK);
    canvas.setTextDatum(middle_center);

    canvas.drawString(
        "Hello PaperDIY!",
        M5.Display.width() / 2,
        M5.Display.height() / 2
    );

    canvas.pushSprite(0, 0);
}

void loop()
{
    M5.update();
}
