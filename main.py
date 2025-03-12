# file: main.py
import pycom
import sys
import time
import os
import machine
import urequests as requests #urequests placed into *lib* directory
from network import WLAN
import ujson
import ufun
import time
from mqtt import MQTTClient
from wificon import WiFiClient
from machine import ADC, Pin, PWM
import utime
from network import LoRa
import socket
import ubinascii


Pin_12='P12'
Pin_16='P16'
is_closed=False
pwm_12 = PWM(0, frequency=50)
pwm_c12 = pwm_12.channel(0, pin=Pin_12, duty_cycle=0.05)
adc = ADC(0)
adc.vref(1120)
authorization_Key = 'HMSRJMTN97XVL8VW'
Http_Update_host = 'https://api.thingspeak.com/'
ssid = ''
net_key = ''

#Connect to mosquito
mosquitto_ip = "mqtt3.thingspeak.com"
mosquitto_port = 1883
device_id = "NiYOAQgOICktLjosKCEFIQY"
mosquitto_uname="NiYOAQgOICktLjosKCEFIQY"
mosquitto_pass="dl3b/+K57J++iZ4ffxtJ4/dF"
channel_id="1998372"

#LOPY
DevEUI=ubinascii.unhexlify("70B3D5499585FCA1")
AppEUI=ubinascii.unhexlify("0059AC00000FFFFF")
AppKey=ubinascii.unhexlify("7AD2B0DDF096AE40F1732AD8820E341C")

# Initialise LoRa in LORAWAN mode.
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868,sf=12)


def sub_cb(topic, msg):
   print("sub_cb(): received on topic={} the msg={}\n".format(topic.decode(), msg.decode()))


def init_LORA():
    print("Lora entered-")
    lora.join(activation=LoRa.OTAA, auth=(DevEUI, AppEUI, AppKey), timeout=0)
    while not lora.has_joined():
        print('Not yet joined...')
        time.sleep(2.5)
    print('Joined')
    # create a LoRa socket
    s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
    # set the LoRaWAN data rate
    s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)
    # send some data
    s.send(bytes([0x01, 0x02, 0x03]))


def init_mqtt():
    global mqttclient
    connect_to_wifi_network_wap2(wlan_mode=WLAN.STA,net_ssid=ssid, key=net_key)
    # connect_to_ufp_wifi()
    mqttclient = MQTTClient(device_id, mosquitto_ip, user=mosquitto_uname, password=mosquitto_pass, port=mosquitto_port)
    mqttclient_connect_mqtt()

    #pwm_c.duty_cycle(0.09 ) # change the duty cycle to 30%
    #mqttclient_pushing(value)
    

def init():
    value=read_light()
    value=4095-value
    value=int(value*100/4095)
    print(value)
    connect_to_wifi_network_wap2(wlan_mode=WLAN.STA,net_ssid=ssid, key=net_key)
    pwm_c12 = pwm_12.channel(0, pin=Pin_12, duty_cycle=0.05)
    #pwm_c.duty_cycle(0.09 ) # change the duty cycle to 30%
    get_http_call(Http_Update_host,value)

    
def connect_to_ufp_wifi():
    ssid='eduroam'
    email='numero@ufp.pt'
    wifipass='pass'
    connect_to_wifi_network_wpa2_ent(wlan_mode=WLAN.STA, net_ssid=ssid, sec_proto=WLAN.WPA2_ENT, username=email , password=wifipass, identity=email, timeout=10000)


def rancheckwifi():
    while True:
        value=read_light()
        value=4095-value
        value=int(value*100/4095)
        print(value)
        pwm_c12 = pwm_12.channel(0, pin=Pin_12, duty_cycle=0.05)
        #pwm_c.duty_cycle(0.09 ) # change the duty cycle to 30%
        get_http_call(Http_Update_host,value)
        check_servo_status(value)
        time.sleep(5)


def rancheckmqtt():
    while True:
        value=read_light()
        value=4095-value
        value=int(value*100/4095)
        print(value)
        pwm_c12 = pwm_12.channel(0, pin=Pin_12, duty_cycle=0.05)
        pwm_c12.duty_cycle(0.0 ) # change the duty cycle to 30%
        #get_http_call(Http_Update_host,value)
        mqttclient_publish(value)
        check_servo_status(value)
        time.sleep(15)


def mqttclient_publish(value):
    global mqttclient
    #mqttclient = MQTTClient(device_id, mosquitto_ip, port=mosquitto_port)
    try:
        topic = "channels/" + channel_id + "/publish"
        tpayload="field1="+str(value)+"&status=MQTTPUBLISH"
        print("main(): Sending sensorvalue={}".format(value))
        mqttclient.publish(topic=topic, msg=tpayload)
    except OSError as err:
        print('main(): cannot connect to broker on addr = {} with err = {}...\n'.format(mosquitto_ip, err))


def mqttclient_connect_mqtt():
    global mqttclient
    print('main(): set callback and connect to broker...')
    print('main(): create MQTT client to broker on addr = {}, port = {}...'.format(mosquitto_ip, mosquitto_port))
    ##Set a callback listening a topic
    mqttclient.set_callback(sub_cb)
    mqttclient.connect()


def check_servo_status(value=100):
    global is_closed
    if (value < 30 and not is_closed):
        pwm_c12.duty_cycle(0.1)
        time.sleep(1)
        pwm_c12.duty_cycle(0.05)
        time.sleep(1)
        pwm_c12.duty_cycle(0)
        is_closed=True
    if (value > 50 and is_closed):
        pwm_c12.duty_cycle(0.1)
        time.sleep(1)
        pwm_c12.duty_cycle(0.05)
        time.sleep(1)
        pwm_c12.duty_cycle(0)
        is_closed=False


def read_light():
    adc_channel_pin  = adc.channel(pin=Pin_16, attn=ADC.ATTN_11DB)
    values = adc_channel_pin.value()
    return values


def get_http_call(url=Http_Update_host,value=-1):
    try:
        test="{}update?api_key={}&field1={}".format(url, authorization_Key, str(value) )
        # Content-Type HTTP header should be set only for PUT and POST requests
        request = requests.get(test)
        reply=request.content.decode()
        # Finally, close response objects to avoid resource leaks and malfunction
        print(test)
        return ""
    except Exception as e:
        print(e)
    return "ff"


def post_http_call(url='http://homepage.ufp.pt/rmoreira/LP2/data.txt',value=""):
    try:
        data = {'api_dev_key':value
        }
        # Content-Type HTTP header should be set only for PUT and POST requests
        request = requests.get(url)
        reply=request.content.decode()
        print("get_http_call(): content="+request.content.decode())
        print("get_http_call(): text="+request.text)

        # Finally, close response objects to avoid resource leaks and malfunction
        request.close()
        return request.json()
    except Exception as e:
        print(e)
    return "ff"


def connect_to_wifi_network_wap2(wlan_mode=WLAN.STA, net_ssid='ssid', sec_proto=WLAN.WPA2, key='wpa2key', timeout=10000):
    print("connect_to_wifi_network_dhcp(net_ssid={}):...".format(net_ssid))
    """ To retrieve the current WLAN instance """
    # The WLAN network class boots in WLAN.AP mode
    #wlan = WLAN()
    # The WLAN net class can boot as STAtion (connect to an existing network)
    wlan = WLAN(mode=wlan_mode)
    print("connect_to_wifi_network_dhcp(): WLAN mode: {}".format(wlan.mode()))

    #Connecting to a Router... Scan for networks:
    nets = wlan.scan()
    for net in nets:
        if net.ssid == net_ssid:
            print("connect_to_wifi_network_dhcp(): Network {} found!".format(net.ssid))
            wlan.connect(ssid=net.ssid, auth=(sec_proto, key), timeout=timeout)
            while not wlan.isconnected():
                machine.idle() # save power while waiting
            print("connect_to_wifi_network_dhcp(): WLAN connection {} success!".format(net_ssid))
            break
        
        
def connect_to_wifi_network_wpa2_ent(wlan_mode=WLAN.STA, net_ssid='ssid', sec_proto=WLAN.WPA2_ENT, username='username@ufp.pt' , password='password', identity='username@ufp.pt', timeout=10000):
    print("connect_to_wifi_network_wpa2_ent(net_ssid={}, username={}):...".format(net_ssid, username))
    """ To retrieve the current WLAN instance """
    # The WLAN network class boots in WLAN.AP mode
    #wlan = WLAN() 
    # The WLAN net class can boot as STAtion (connect to an existing network) 
    wlan = WLAN(mode=wlan_mode)
    print("connect_to_wifi_network_wpa2_ent(): WLAN mode: {}".format(wlan.mode()))

    #Connecting to a Router...
    # Scan for networks:
    nets = wlan.scan()
    for net in nets:
        if net.ssid == net_ssid:
            print("connect_to_wifi_network_wpa2_ent(): Network {} found!".format(net.ssid))
            """
            #Connecting with EAP-PEAP (provide username and password pair; if necessary provide also client key and certificate):
            wlan.connect(ssid='eduroam', auth=(WLAN.WPA2_ENT, 'convidado@ufp', '012938'), identity='convidado@ufp', timeout=timeout)
            wlan.connect(ssid='eduroam', auth=(WLAN.WPA2_ENT, 'convidado@ufp', '012938'), identity='convidado@ufp', ca_certs='/flash/cert/ca.pem')
            #Connecting with EAP-TLS (copy keys pair K+/K- to device /flash/cert):
            #To validate server’s public key, provide also appropriate CA certificate (chain)
            wlan.connect(ssid='eduroam', auth=(WLAN.WPA2_ENT,), identity='username@ufp.pt', ca_certs='/flash/cert/ca.pem', keyfile='/flash/cert/client.key', certfile='/flash/cert/client.crt')
            """ 
            wlan.connect(ssid=net.ssid, auth=(sec_proto, username, password), identity=identity, timeout=timeout)
            while not wlan.isconnected():
                machine.idle() # save power while waiting
            print("connect_to_wifi_network_wpa2_ent(): WLAN connection {} success!".format(net_ssid))
            break


def main():
    print("Hello World!")
    #init_LORA()
    #init()
    #rancheckwifi()

    init_mqtt()
    rancheckmqtt()


if __name__ == "__main__":
    main()
