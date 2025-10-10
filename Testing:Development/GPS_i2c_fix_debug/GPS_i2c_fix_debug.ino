/*
  Get fix type and RTK fix type if available
  By: Nathan Seidle
  SparkFun Electronics
  Date: January 3rd, 2019
  License: MIT. See license file for more information.

  This example shows how to query a u-blox module for fix type and RTK fix type.
  The fix type is as follows:
    0 = no fix
    1 = dead reckoning (requires external sensors)
    2 = 2D (not quite enough satellites in view)
    3 = 3D (the standard fix)
    4 = GNSS + dead reckoning (requires external sensors)
    5 = Time fix only

  Additionally, if we are doing RTK, we can figure out if we have a floating 
  RTK solution or if we have been able to resolve a fixec solution (better precision).

  Leave NMEA parsing behind. Now you can simply ask the module for the datums you want!

  Feel like supporting open source hardware?
  Buy a board from SparkFun!
  SparkFun GPS-RTK2 - ZED-F9P (GPS-15136)    https://www.sparkfun.com/products/15136
  SparkFun GPS-RTK-SMA - ZED-F9P (GPS-16481) https://www.sparkfun.com/products/16481
  SparkFun MAX-M10S Breakout (GPS-18037)     https://www.sparkfun.com/products/18037
  SparkFun ZED-F9K Breakout (GPS-18719)      https://www.sparkfun.com/products/18719
  SparkFun ZED-F9R Breakout (GPS-16344)      https://www.sparkfun.com/products/16344

  Hardware Connections:
  Plug a Qwiic cable into the GNSS and a BlackBoard
  If you don't have a platform with a Qwiic connection use the SparkFun Qwiic Breadboard Jumper (https://www.sparkfun.com/products/14425)
  Open the serial monitor at 115200 baud to see the output
*/

#include <Wire.h> //Needed for I2C to GNSS

#include <SparkFun_u-blox_GNSS_v3.h> //http://librarymanager/All#SparkFun_u-blox_GNSS_v3
SFE_UBLOX_GNSS myGNSS;

long lastTime = 0; //Simple local timer. Limits amount if I2C traffic to u-blox module.
unsigned long startTime = 0; //Used to calc the actual update rate.
unsigned long updateCount = 0; //Used to calc the actual update rate.

void setup()
{
  Serial.begin(115200);
  Serial.println("SparkFun u-blox Example");

  Wire.begin();
  //Wire.setClock(400000); //Optional. Increase I2C clock speed to 400kHz.

  if (myGNSS.begin() == false) //Connect to the u-blox module using Wire port
  {
    Serial.println(F("u-blox GNSS not detected at default I2C address. Please check wiring. Freezing."));
    while (1);
  }

  myGNSS.setNavigationFrequency(5); //Set output to 5 times a second

  uint8_t rate = myGNSS.getNavigationFrequency(); //Get the update rate of this module
  Serial.print("Current update rate: ");
  Serial.println(rate);

}

void loop()
{



  //Query module only every second. Doing it more often will just cause I2C traffic.
  if (millis() - lastTime > 500)
  {
    lastTime = millis(); //Update the timer
    updateCount++;

    long latitude = myGNSS.getLatitude();
    Serial.print(F("Lat: "));
    Serial.print(latitude);

    long longitude = myGNSS.getLongitude();
    Serial.print(F(" Long: "));
    Serial.print(longitude);

    long altitude = myGNSS.getAltitude();
    Serial.print(F(" Alt: "));
    Serial.print(altitude);
    Serial.print(F(" (mm)"));

    long altitudeMSL = myGNSS.getAltitudeMSL();
    Serial.print(F(" AltMSL: "));
    Serial.print(altitudeMSL);
    Serial.print(F(" (mm)"));

    byte fixType = myGNSS.getFixType();
    Serial.print(F(" Fix: "));
    if(fixType == 0) Serial.print(F("No fix"));
    else if(fixType == 1) Serial.print(F("Dead reckoning"));
    else if(fixType == 2) Serial.print(F("2D"));
    else if(fixType == 3) Serial.print(F("3D"));
    else if(fixType == 4) Serial.print(F("GNSS + Dead reckoning"));
    else if(fixType == 5) Serial.print(F("Time only"));

        byte SIV = myGNSS.getSIV();
    Serial.print(F(" SIV: "));
    Serial.print(SIV);

    Serial.println();
    Serial.print(myGNSS.getYear());
    Serial.print("-");
    Serial.print(myGNSS.getMonth());
    Serial.print("-");
    Serial.print(myGNSS.getDay());
    Serial.print(" ");
    Serial.print(myGNSS.getHour());
    Serial.print(":");
    Serial.print(myGNSS.getMinute());
    Serial.print(":");
    Serial.print(myGNSS.getSecond());

    Serial.print("  Time is ");
    if (myGNSS.getTimeValid() == false)
    {
      Serial.print("not ");
    }
    Serial.print("valid  Date is ");
    if (myGNSS.getDateValid() == false)
    {
      Serial.print("not ");
    }
    Serial.print("valid");

    Serial.println();

    long speed = myGNSS.getGroundSpeed();
    Serial.print(F(" Speed: "));
    Serial.print(speed);
    Serial.print(F(" (mm/s)"));

    long heading = myGNSS.getHeading();
    Serial.print(F(" Heading: "));
    Serial.print(heading);
    Serial.print(F(" (degrees * 10^-5)"));

    int pDOP = myGNSS.getPDOP();
    Serial.print(F(" pDOP: "));
    Serial.print(pDOP / 100.0, 2); // Convert pDOP scaling from 0.01 to 1

    Serial.println();

    Serial.print(F(" Rate: "));
    Serial.print( updateCount / ((millis() - startTime) / 1000.0), 2);
    Serial.print(F("Hz"));

    Serial.println();

    // RTK is not applicable for BUTM, because it requires additional setup & resources.
    // byte RTK = myGNSS.getCarrierSolutionType();
    // Serial.print(" RTK: ");
    // Serial.print(RTK);
    // if (RTK == 0) Serial.print(F(" (No solution)"));
    // else if (RTK == 1) Serial.print(F(" (High precision floating fix)"));
    // else if (RTK == 2) Serial.print(F(" (High precision fix)"));
    // Serial.println();
  }

}
