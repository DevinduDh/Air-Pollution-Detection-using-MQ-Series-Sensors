import RPi.GPIO as GPIO
import time
import math
from tqdm import tqdm
from firebase import firebase

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

firebase = firebase.FirebaseApplication('https://air-quality-c164a-default-rtdb.firebaseio.com')
#port init
def init():
         GPIO.setwarnings(False)
         GPIO.cleanup()          #clean up at the end of your script
         GPIO.setmode(GPIO.BCM)       #to specify whilch pin numbering system
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
        
        # A dict with sensors and their load resistances
        sensor_apins = {mq135_apin : 20, mq2_apin: 20, mq4_apin: 20}
        # sensor_apins = (mq135_apin, mq2_apin)
        R0_list = []
        analog_read = readadc(1,SPICLK,SPIMOSI,SPIMISO,SPICS)
        print("analog_read: {}".format(analog_read))
        for j in tqdm(sensor_apins):
                m = 0
                #print(j)
                sensor_volt = None
                RS_air = None
                R0 = None
                sensor_value = 0.0            
                analog_read = readadc(j,SPICLK,SPIMOSI,SPIMISO,SPICS)
                #print("analog_read: {}".format(analog_read))
                #print("check")

                
                for x in range(5000):
                    if m != 500:
                        if analog_read != 0 and analog_read <= 1023:
                            #print("check1")
                            sensor_value = sensor_value + analog_read
                            m = m + 1
                        elif analog_read > 1023:
                            analog_read = 1023
                            sensor_value = sensor_value + analog_read
                            m = m + 1
                        else:
                            pass
                    elif m == 500:
                        sensor_value = sensor_value/500.0
                        #print("sensor {}:{}".format(j,sensor_value))
                        sensor_volt = sensor_value*(5.0/1023.0)
                        #print("sensor_volt:{}(in caliberating)".format(sensor_volt))
                        #print("sensor_apins[j] {}:".format(sensor_apins[j]))
                        RS_air = ((5.0*sensor_apins[j])/sensor_volt) - 10.0
                        #print("RS_air:{}".format(RS_air))
                        if j == mq135_apin:
                            ratio_air = 3.7
                        elif j == mq2_apin:
                            ratio_air = 9.8
                        elif j == mq4_apin:
                            ratio_air = 4.4
                        R0 = RS_air/ratio_air

                        R0_list.append(R0)
                        time.sleep(0.5)
                        break
        print(R0_list)
        print("Caliberating Done")
        return R0_list

def mq135_Calc(R0):
        #print("inside mq135 calc")
        loadRes = 20
        #Calculating for smoke
        m = -0.318
        b = 1.13
        sensorVal = readadc(mq135_apin, SPICLK, SPIMOSI, SPIMISO, SPICS)
        #print("sensorVal: {}".format(sensorVal))
        if sensorVal !=0 and sensorVal <= 1023:
                sensor_volt = sensorVal*(5.0/1023.0)
                #print("sensor_volt(<=1023): {}".format(sensor_volt))
                RS_gas = ((5.0*loadRes)/sensor_volt) - 10
                #print("RS_gas: {}".format(RS_gas))
                ratio = RS_gas/R0
                #print("ratio: {}".format(ratio))
                if ratio >0:
                    ppm_log = (math.log10(ratio) - b)/m
                    ppm = pow(10, ppm_log)
                    percentage = ppm/10000
                    return ppm
                else:
                    pass
        elif sensorVal > 1023:
                sensorVal = 1023
                sensor_volt = sensorVal*(5.0/1023.0)
                #print("sensor_volt(>1023): {}".format(sensor_volt))
                RS_gas = ((5.0*loadRes)/sensor_volt) - 10
                ratio = RS_gas/R0
                #print("ratio: {}".format(ratio))
                if ratio >0:
                    ppm_log = (math.log10(ratio) - b)/m
                    ppm = pow(10, ppm_log)
                    percentage = ppm/10000
                    return ppm
                else:
                    pass
        elif sensorVal == 0:
                pass
def mq2_Calc(R0):
        #calculations for smoke
        #print("Inside mq2")
        loadRes = 20
        #print(R0)
        m = -0.476
        b = 1.683
        sensorVal = readadc(mq2_apin, SPICLK, SPIMOSI, SPIMISO, SPICS)
        #print("sensor_val: {}".format(sensorVal))
        if sensorVal !=0 and sensorVal <= 1023:
            
            sensor_volt = sensorVal*(5.0/1023.0)
            #print("sensor_volt(<=1023): {}".format(sensor_volt))
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            #print("RS_gas: {}".format(RS_gas))
            ratio = RS_gas/R0
            #print("ratio: {}".format(ratio))
            if ratio >0:
                ppm_log = (math.log10(ratio) - b)/m
                ppm = pow(10, ppm_log)
                percentage = ppm/10000
                return ppm
            else:
                pass
        elif sensorVal > 1023:
            sensorVal = 1023
            sensor_volt = sensorVal*(5.0/1023.0)
            #print("sensor_volt(>1023): {}".format(sensor_volt))
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            ratio = RS_gas/R0
            #print("ratio: {}".format(ratio))
            if ratio >0:
                ppm_log = (math.log10(ratio) - b)/m
                ppm = pow(10, ppm_log)
                percentage = ppm/10000
                return ppm
            else:
                pass
        elif sensorVal == 0:
            pass

    
def mq4_Calc(R0):
        loadRes = 20
        #calculating for LPG
        m = -0.318
        b = 1.13
        sensorVal = readadc(mq4_apin, SPICLK, SPIMOSI, SPIMISO, SPICS)
        if sensorVal !=0 and sensorVal <= 1023:
            
            sensor_volt = sensorVal*(5.0/1023.0)
            #print("sensor_volt(<=1023): {}".format(sensor_volt))
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            #print("RS_gas: {}".format(RS_gas))
            ratio = RS_gas/R0
            #print("ratio: {}".format(ratio))
            if ratio >0:
                ppm_log = (math.log10(ratio) - b)/m
                ppm = pow(10, ppm_log)
                percentage = ppm/10000
                return ppm
            else:
                pass
        elif sensorVal > 1023:
            sensorVal = 1023
            sensor_volt = sensorVal*(5.0/1023.0)
            #print("sensor_volt(>1023): {}".format(sensor_volt))
            RS_gas = ((5.0*loadRes)/sensor_volt) - 10
            ratio = RS_gas/R0
            #print("ratio: {}".format(ratio))
            if ratio >0:
                ppm_log = (math.log10(ratio) - b)/m
                ppm = pow(10, ppm_log)
                percentage = ppm/10000
                return ppm
            else:
                pass
        elif sensorVal == 0:
            pass


#main ioop
def main():
         init()
         
         print("please wait...")
         print("Starting Caliberaing sensors")
         R0_list = caliberate()

         print("processing")
         time.sleep(5)
         print(GPIO.input(mq2_dpin))
         print(GPIO.input(mq135_dpin))
         print(GPIO.input(mq4_dpin))
         while True:
                  if GPIO.input(mq2_dpin) == 1 and GPIO.input(mq135_dpin) == 0 and GPIO.input(mq4_dpin) == 1:
                    pass
#                      print("Normal")
#                      time.sleep(0.5)    
                  else:
                     print("Gas leakage")
                     #print("Current Gas AD vaule = " +str("%.2f"%((COlevel/1024.)*3.3))+" V")
                     time.sleep(0.5)
                    
                  # Assigning ppm values to temp variables in case of null values    
                  mq135_ppm = mq135_Calc(R0_list[0])
                  if mq135_ppm  !=  None:
                      mq135_ppm_temp = mq135_ppm
                  
                  mq2_ppm = mq2_Calc(R0_list[1])
                  if mq2_ppm  !=  None:
                      mq2_ppm_temp = mq2_ppm
                  
                  mq4_ppm = mq4_Calc(R0_list[2])
                  if mq2_ppm  !=  None:    
                      mq4_ppm_temp = mq4_ppm
                  

#                   print("ppm from mq135: {}".format(mq135_ppm))
                  if mq135_ppm != None:
                      print("ppm from mq135: {}".format(mq135_ppm))
                  else:
                      try:
                          print("ppm from mq135: {}".format(mq135_ppm_temp))
                      except:
                          pass
#                       
#                     
                  if mq2_ppm != None:
                      print("ppm from mq2: {}".format(mq2_ppm))
                  else:
                      try:
                          print("ppm from mq2: {}".format(mq2_ppm_temp))
                      except:
                          pass
               

                  if mq4_ppm != None:
                      print("ppm from mq4: {}".format(mq4_ppm))
                  else:
                      try:
                          print("ppm from mq4: {}".format(mq4_ppm_temp))
                      except:
                          pass
                  print(" ")
                  
                  
                  if mq135_ppm == None and mq2_ppm == None and mq4_ppm == None: 
                      result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm_temp),'mq2_ppm':str(mq2_ppm_temp),'mq4_ppm':str(mq4_ppm_temp)})
                  elif mq135_ppm == None and mq2_ppm != None and mq4_ppm != None:
                      result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm_temp),'mq2_ppm':str(mq2_ppm),'mq4_ppm':str(mq4_ppm)})
                  elif mq135_ppm != None and mq2_ppm == None and mq4_ppm != None:
                      try:
                          result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm),'mq2_ppm':str(mq2_ppm_temp),'mq4_ppm':str(mq4_ppm)})
                      except:
                          result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm),'mq2_ppm':str(mq2_ppm),'mq4_ppm':str(mq4_ppm)})                          
                  elif mq135_ppm != None and mq2_ppm != None and mq4_ppm == None:
                      result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm),'mq2_ppm':str(mq2_ppm),'mq4_ppm':str(mq4_ppm_temp)})                  
                  elif mq135_ppm == None and mq2_ppm == None and mq4_ppm != None:
                      try:
                          result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm_temp),'mq2_ppm':str(mq2_ppm_temp),'mq4_ppm':str(mq4_ppm)})
                      except:
                          result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm),'mq2_ppm':str(mq2_ppm),'mq4_ppm':str(mq4_ppm)}) 
                  elif mq135_ppm == None and mq2_ppm != None and mq4_ppm == None:
                      result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm_temp),'mq2_ppm':str(mq2_ppm),'mq4_ppm':str(mq4_ppm_temp)})             
                  elif mq135_ppm != None and mq2_ppm == None and mq4_ppm == None:
                      result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm),'mq2_ppm':str(mq2_ppm_temp),'mq4_ppm':str(mq4_ppm_temp)})
                  else:
                      result = firebase.post('Air-Quality',{'mq135_ppm':str(mq135_ppm),'mq2_ppm':str(mq2_ppm),'mq4_ppm':str(mq4_ppm)})
                  time.sleep(5)


if __name__ =='__main__':
         try:
                  
                  main()
                  pass
         except KeyboardInterrupt:
                  pass

GPIO.cleanup()
         
