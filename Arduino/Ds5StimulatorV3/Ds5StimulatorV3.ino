/**
  Digitimer DS5 stimulator signal generator
  Leiden University - Evert Dekker 2020
  Mkr Zero
  
  1.0 20200303  Initial Release
  1.1 20200709  Current setting changed to 25mA. Max current (25mA/5V)*3.3V= 16.5mA
  1.2 20201130  Max.Pulses increased from 100 to 3000. Feedback also changed to max min for more then 100 pulses - NOT released, to memory hunger
  1.3 20201201  Max.Pulses increased to 20000

**/

#include "avdweb_AnalogReadFast.h"   //Needed because default arduino driver takes 865uS for a AD sample, this lib only takes 35uS
#include <ArduinoJson.h>

#define DS5_uAmp 25000 // DS5 Settings in micro amps
#define DS5_V 5        // DS5 Settings in Volts
#define DAC_maxcount pow(2,10) //10 bits
#define DAC_Vref 3.3   //3.3Volts reference
#define ADC_maxcount pow(2,12) //12 bits
#define ADC_Vref 3.3  // 3.3Volts reference
#define ADC_CURRENT_PIN 1
#define ADC_VOLTAGE_PIN 2

#define MAX_PULSES 20000
#define LOOPCORRECTION  70 // Correction for the stimules loop in uS
#define LOOPCORRECTION_LARGE  110 // Correction for the stimules loop in uS sendpulses 

const String Version = "1.3";
const String Serialno = "S00760";   //** NOTE **, if you reflash the device chnage this according the serialnumber. Arduino MKT doesn't have eeprom to store this.
String incoming = "";   // for incoming serial string data

typedef struct {
  word current;
  word volt;
} adcread;

word maxcurrentcount = 0, mincurrentcount = 65535;
word maxvoltcount = 0, minvoltcount = 65535;
word tempadcvalue;
adcread adcvalue[110];
DynamicJsonDocument doc(250);
DynamicJsonDocument result(5000);

void setup() {
  Serial.begin(115200);
  analogWriteResolution(10);  //DAC resolution
  analogWrite(A0, 0);         // Initialize Dac  to Zero
  analogReadResolution(12);   //ADC resolution
  while (!Serial);   //wait for cdc serial port to be ready
}

void loop() {
  if (Serial.available() > 0) {
    incoming = Serial.readStringUntil('\n');                                                  // Until LF
    deserializeJson(doc, incoming);                                                             //Test json-string {"current":3.3, "Ton":1.0, "Toff":3.5,"repeat":3}  Response: {"samples":3,"current":[3.13,3.17,3.17],"voltage":[4,3,3]}
    JsonObject obj = doc.as<JsonObject>();
    float current = obj["current"], Ton = obj["Ton"], Toff = obj["Toff"];
    unsigned int repeat = obj["repeat"];
    unsigned int _current = current * 1000, _Ton = Ton * 1000, _Toff = Toff * 1000;            //cast float (mAmp, mS) values in int * 1000 for uAmp and uSec
    if (!validatevalues (_current, _Ton, _Toff, repeat)) {
      if (repeat < 101) {
        sendpulse (_current, _Ton, _Toff, repeat);
      }
      else  {
        sendpulseLarge (_current, _Ton, _Toff, repeat);  // More then 100 pulses
      }
    }
  }
}

bool validatevalues(unsigned int uAmp , unsigned int Ton, unsigned int Toff, unsigned int repeat) {
  if (uAmp > ((DS5_uAmp / DS5_V)*DAC_Vref) - 100 ) {                                          // Requested current can't be higher then settings of the DS5. Minus 100 as safety because the DAC sometimes rollsover with max value TODO Check why.
    printerror(1, "Requested current " + String(uAmp) +  "uA to high for this configuration.");
    return true;
  }
  if (Ton < 100) {
    printerror(2, "Pulsduration must be at least 100 uS");
    return true;
  }
  if (repeat >= MAX_PULSES) {
    printerror(3, "No more then " + String(MAX_PULSES) + " pulses allowed");
    return true;
  }
  return false;   //everything fine
}


void sendpulseLarge(unsigned int uAmp , unsigned int Ton, unsigned int Toff, unsigned int repeat) {  //Send pulses with an greater then 100
  maxcurrentcount = 0, mincurrentcount = 65535;     //Reset the variable to default value
  maxvoltcount = 0, minvoltcount = 65535;
  Ton = (Ton - LOOPCORRECTION_LARGE) / 2 ;
  for (int i = 1; i <= repeat; i++) {
    analogWrite(A0, microamp2count(uAmp));
    delayMicroseconds(Ton);

    tempadcvalue = (analogReadFast(ADC_CURRENT_PIN));   //Sample in the middle of the pulse both ADC channels
    if (tempadcvalue > maxcurrentcount) {               // Check to see if the new value is a new max
      maxcurrentcount = tempadcvalue;
    }
    if (tempadcvalue < mincurrentcount) {               // Check to see if the new value is a new min
      mincurrentcount =  tempadcvalue;
    }

    tempadcvalue = (analogReadFast(ADC_VOLTAGE_PIN));
    if (tempadcvalue > maxvoltcount) {
      maxvoltcount = tempadcvalue;
    }
    if (tempadcvalue < minvoltcount) {
      minvoltcount =  tempadcvalue;
    }
    delayMicroseconds(Ton);
    analogWrite(A0, 0);
    delayMicroseconds(Toff);
  }
  printresultMaxMin(repeat);
}

void sendpulse(unsigned int uAmp , unsigned int Ton, unsigned int Toff, unsigned int repeat) {   //Send pulses with an repeat less the 100
  Ton = (Ton - LOOPCORRECTION) / 2 ;
  for (int i = 1; i <= repeat; i++) {
    analogWrite(A0, microamp2count(uAmp));
    delayMicroseconds(Ton);
    adcvalue[i].current = (analogReadFast(ADC_CURRENT_PIN));   //Sample in the middle of the pulse both ADC channels
    adcvalue[i].volt = (analogReadFast(ADC_VOLTAGE_PIN));
    delayMicroseconds(Ton);
    analogWrite(A0, 0);
    delayMicroseconds(Toff);
  }
  printresult(repeat);
}

void printresult(unsigned int samples) {                      //Prints the measured results of the pulses
  result.clear();                                            //Cear the previous stuff from the Json document
  result["Ver"] = Version;
  result["Serial"] = Serialno;
  result["samples"] = samples;
  JsonArray current = result.createNestedArray("current");
  JsonArray voltage = result.createNestedArray("voltage");
  for (int i = 1; i <= samples; i++) {
    current.add(count2milliamp(adcvalue[i].current));
    voltage.add(count2volt(adcvalue[i].volt));
  }
  serializeJson(result, Serial);
  Serial.println();
}

void printresultMaxMin(unsigned int samples) {                      //Prints the measured results of the pulses
  result.clear();
  result["Ver"] = Version;
  result["Serial"] = Serialno;
  result["samples"] = samples;
  result["MaxCurrent"] = count2milliamp(maxcurrentcount);
  result["MinCurrent"] = count2milliamp(mincurrentcount);
  result["MaxVolt"] = count2volt(maxvoltcount);
  result["MinVolt"] = count2volt(minvoltcount);
  serializeJson(result, Serial);
  Serial.println();
}



void printerror(unsigned int errornumber, String error) {
  String str = "{\"Error#\":";
  str += errornumber;
  str += ",\"Error\":";
  str += error;
  str += "}";
  Serial.println(str);
}

unsigned int microamp2count(unsigned int uAmp) {
  return uAmp / ((DS5_uAmp / DS5_V) * (DAC_Vref / DAC_maxcount));
}

float count2milliamp(unsigned int count) {
  return round2((ADC_Vref / ADC_maxcount) * count * (10 / 1));  // (ADC ref / ADC resolution) * measured adc value * (10ma / 1V)
}

unsigned int count2volt(unsigned int count) {
  return (ADC_Vref / ADC_maxcount) * count * (20 / 1) * 5 / ADC_Vref; // ADCstep * count * 1V per 20V output * voltage divider
}

float round2(float value) {
  return (int)(value * 100 + 0.5) / 100.0;
}

