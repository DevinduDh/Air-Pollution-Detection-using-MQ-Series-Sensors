import RPi.GPIO as GPIO
import time
import math

# change these as desired - they're the pins connected from the
# SPI port on the ADC to the Cobbler
SPICLK = 11
SPIMISO = 9
SPIMOSI = 10
SPICS = 8
mq2_dpin = 26
mq2_apin = 1

mq135_dpin = 20
mq135_apin = 0

mq4_dpin = 21
mq4_apin = 2

#port init
def init():
         GPIO.setwarnings(False)
         GPIO.cleanup()			#clean up at the end of your script
         GPIO.setmode(GPIO.BCM)		#to specify whilch pin numbering system
         # set up the SPI interface pins
         GPIO.setup(SPIMOSI, GPIO.OUT)
         GPIO.setup(SPIMISO, GPIO.IN)
         GPIO.setup(SPICLK, GPIO.OUT)
         GPIO.setup(SPICS, GPIO.OUT)
         GPIO.setup(mq2_dpin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
         GPIO.setup(mq135_dpin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
         GPIO.setup(mq4_dpin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

#read SPI data from MCP3008(or MCP3204) chip,8 possible adc's (0 thru 7)
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
        if ((adcnum > 7) or (adcnum < 0)):
                return -1
        GPIO.output(cspin, True)	

        GPIO.output(clockpin, False)  # start clock low
        GPIO.output(cspin, False)     # bring CS low

        commandout = adcnum
        commandout |= 0x18  # start bit + single-ended bit
        commandout <<= 3    # we only need to send 5 bits here
        for i in range(5):
                if (commandout & 0x80):
                        GPIO.output(mosipin, True)
                else:
                        GPIO.output(mosipin, False)
                commandout <<= 1
                GPIO.output(clockpin, True)
                GPIO.output(clockpin, False)

        adcout = 0
        # read in one empty bit, one null bit and 10 ADC bits
        for i in range(12):
                GPIO.output(clockpin, True)
                GPIO.output(clockpin, False)
                adcout <<= 1
                if (GPIO.input(misopin)):
                        adcout |= 0x1

        GPIO.output(cspin, True)
        
        adcout >>= 1       # first bit is 'null' so drop it
        return adcout
    
def caliberate():
        sensor_apins = {mq135_apin : 10, mq2_apin: 5, mq4_apin: 20}
        # sensor_apins = (mq135_apin, mq2_apin)
        R0_list = []

        for j in sensor_apins:
                #print(j)
                sensor_volt = None
                RS_air = None
                R0 = None
                sensor_value = 0.0            
                analog_read = readadc(j,SPICLK,SPIMOSI,SPIMISO,SPICS)

                for x in range(500):
                    if analog_read <= 1023:
                        sensor_value = sensor_value + analog_read
                    else:
                        analog_read = 1023
                        sensor_value = sensor_value + analog_read                   
                sensor_value = sensor_value/500.0
                sensor_volt = sensor_value*(5.0/1023.0)
                RS_air = ((5.0*sensor_apins[j])/sensor_volt) - 10.0
                if j == mq135_apin:
                    ratio_air = 3.7
                elif j == mq2_apin:
                    ratio_air = 9.8
                elif j == mq4_apin:
                    ratio_air = 4.4
                R0 = RS_air/ratio_air

                R0_list.append(R0)
        time.sleep(10)
        print("Caliberating Done")
        return R0_list

def mq135_Calc(R0):
        loadRes = 10
        m = -0.318
        b = 1.13
        sensorVal = readadc(mq135_apin, SPICLK, SPIMOSI, SPIMISO, SPICS)
        if sensorVal <= 1023:
            sensor_volt = sensorVal*(5.0/1023.0)
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            ratio = RS_gas/R0
#             ppm_log = (math.log10(ratio) - b)/m
#             ppm = pow(10, ppm_log)
#             percentage = ppm/10000
        else:
            sensorVal = 1023
            sensor_volt = sensorVal*(5.0/1023.0)
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            ratio = RS_gas/R0
#             ppm_log = (math.log10(ratio) - b)/m
#             ppm = pow(10, ppm_log)
#             percentage = ppm/10000
#         return ppm
def mq2_Calc(R0):
        #calculations for smoke
        loadRes = 5
        print(R0)
        m = -0.476
        b = 1.683
        sensorVal = readadc(mq2_apin, SPICLK, SPIMOSI, SPIMISO, SPICS)
        if sensorVal <= 1023:
            sensor_volt = sensorVal*(5.0/1023.0)
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            ratio = RS_gas/R0
#             ppm_log = (math.log10(ratio) - b)/m
#             ppm = pow(10, ppm_log)
#             percentage = ppm/10000
        else:
            sensorVal = 1023
            sensor_volt = sensorVal*(5.0/1023.0)
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            ratio = RS_gas/R0
#             ppm_log = (math.log10(ratio) - b)/m
#             ppm = pow(10, ppm_log)
#             percentage = ppm/10000
#         return ppm
    
def mq4_Calc(R0):
        loadRes = 20
        #calculating for LPG
        m = -0.318
        b = 1.13
        sensorVal = readadc(mq4_apin, SPICLK, SPIMOSI, SPIMISO, SPICS)
        if sensorVal <= 1023:
            sensor_volt = sensorVal*(5.0/1023.0)
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            ratio = RS_gas/R0
            ppm_log = (math.log10(ratio) - b)/m
            ppm = pow(10, ppm_log)
            percentage = ppm/10000
        else:
            sensorVal = 1023
            sensor_volt = sensorVal*(5.0/1023.0)
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            ratio = RS_gas/R0
            ppm_log = (math.log10(ratio) - b)/m
            ppm = pow(10, ppm_log)
            percentage = ppm/10000
        return ppm

#main ioop
def main():
         init()
         
         print("please wait...")
         print("Starting Caliberaing sensors")
         print("-----------------------------")
         R0_list = caliberate()
         print(R0_list)
         k = GPIO.input(mq2_dpin)
         #print("mq2: {}".format(k))
#          j = GPIO.input(mq135_dpin)
#          print("mq135: {}".format(j))
         time.sleep(20)
         while True:
                  mq135_ppm = mq135_Calc(R0_list[0])
                  mq2_ppm = mq2_Calc(R0_list[1])
                  mq4_ppm = mq4_Calc(R0_list[2])
#                   print("ppm from mq135: {}".format(mq135_ppm))
#                   print("ppm from mq2: {}".format(mq2_ppm))
#                   print("ppm from mq4: {}".format(mq4_ppm))                
#                 
# 
#                 if GPIO.input(mq2_dpin) == 1 and GPIO.input(mq135_dpin) == 1:
#                      print("Normal")
#                      time.sleep(0.5)    
#                 else:
#                      print("Gas leakage")
#                      #print("Current Gas AD vaule = " +str("%.2f"%((COlevel/1024.)*3.3))+" V")
#                      time.sleep(0.5)

if __name__ =='__main__':
         try:
                  
                  main()
                  pass
         except KeyboardInterrupt:
                  pass

GPIO.cleanup()
         
         
