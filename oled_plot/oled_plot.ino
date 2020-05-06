#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels

#define OLED_MOSI   9
#define OLED_CLK   10
#define OLED_DC    11
#define OLED_CS    12
#define OLED_RESET 13
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, OLED_MOSI, OLED_CLK, OLED_DC, OLED_RESET, OLED_CS);
//Adafruit_SSD1306 display(OLED_MOSI, OLED_CLK, OLED_DC, OLED_RESET, OLED_CS);

StaticJsonDocument<100> doc;

void setup()   {

	display.begin(SSD1306_SWITCHCAPVCC);
  	display.setTextColor(SSD1306_BLACK);
	display.clearDisplay();
	display.invertDisplay(true);
  	display.setCursor(0, 0);
  	display.setTextSize(1); // Draw 2X-scale text
	Serial.begin(9600);

}

void loop() {
	if (Serial.available()) {
		DeserializationError error  = deserializeJson(doc, Serial);
		if (error) {
			display.println(F("error"));
			display.display();
		}
		display.drawPixel(doc["xy"][0], doc["xy"][1], SSD1306_WHITE);	
		display.display();
	}

}

