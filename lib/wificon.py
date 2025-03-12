# @author Rui S. Moreira
# December 2021
# Class with useful wifi functionality:
import pycom
import time
import os
import machine
from network import WLAN


class WiFiException(Exception):
    pass

class WiFiClient(object):

    def __init__(self, wlan, ssid='eduroam', netsec = WLAN.WPA2, timeout=10000, username='convidado@ufp', password='01234', identity='convidado@ufp', cacerts='/flash/cert/ca.pem', keyfile='/flash/cert/client.key', certfile='/flash/cert/client.crt'):
        #self.wlan_mode = wlan_mode
        self.wlan = wlan
        self.ssid = ssid
        self.netsec = netsec
        self.timeout = timeout
        self.username = username
        self.password = password
        self.identity = identity
        self.cacerts = cacerts
        self.keyfile = keyfile
        self.certfile = certfile
        # The WLAN network class boots in WLAN.AP mode: wlan = WLAN() 
        # Can boot as STA(tion) to connect to an existing network
        #self.wlan = wlan #WLAN(mode=WLAN.STA)
        print("WiFiClient(): WLAN.mode = {}, ssid = {}, netsec = {}".format(wlan.mode(), ssid, netsec))

    @classmethod
    def create_with_wifi_config(cls, wlan, ssid, wifi_config):
        #netsec = wifi_config.get('netsec', WLAN.WPA2)
        netsec_str=wifi_config.get('netsec', 'WPA2')
        netsec = WiFiClient.netsec_name_to_netsec(netsec_str)
        timeout = wifi_config.get('timeout', 5000)
        username = wifi_config.get('username', None)
        password = wifi_config.get('password', None)
        identity = wifi_config.get('identity', None)
        cacerts = wifi_config.get('cacerts', None)
        keyfile = wifi_config.get('keyfile', None)
        certfile = wifi_config.get('certfile', None)
        broker_addr_or_ip = wifi_config.get('brokerip', 'localhost')
        print("create_with_wifi_config(): wifi_config = ({},{},{})".format(ssid, netsec_str, broker_addr_or_ip))
        return cls(wlan, ssid, netsec, timeout, username, password, identity, cacerts, keyfile, certfile)

    @staticmethod
    def netsec_name(netsec=WLAN.WPA2):
        switcher = {
            WLAN.WPA: 'WPA',
            WLAN.WPA2: 'WPA2',
            WLAN.WPA2_ENT: 'WPA2_ENT',
            WLAN.WEP: 'WEP'
        }
        return switcher.get(netsec, 'NA')

    @staticmethod
    def netsec_name_to_netsec(netsec_name='WPA2'):
        switcher = {
            'WPA': WLAN.WPA,
            'WPA2': WLAN.WPA2,
            'WPA2_ENT': WLAN.WPA2_ENT,
            'WEP': WLAN.WEP
        }
        return switcher.get(netsec_name, 'NA')

    def connect_to_wifi_network(self):
        print('connect_to_wifi_network(): going to connect ssid = {}, netsec = {}...'.format(self.ssid, WiFiClient.netsec_name(self.netsec)))
        # Get the function from switcher dictionary and execute it
        switcher = {
            WLAN.WPA: 'connect_wpa',
            WLAN.WPA2: 'connect_wpa2',
            WLAN.WPA2_ENT: 'connect_wpa2_ent',
            WLAN.WEP: 'connect_wep'
            #WLAN.TTLS: 'connect_eap_peap_or_ttls'
        }
        connect_func_name = switcher.get(self.netsec)
        connect_func = getattr(self, connect_func_name, lambda :'NA')
        connect_func()
        while not self.wlan.isconnected():
            machine.idle() # save power while waiting
        wlanconfig = self.wlan.ifconfig() 
        print('connect_to_wifi_network(): WLAN connection succeeded details = {}'.format(wlanconfig))

    def scan_and_connect_to_wifi_network(self):
        #Connecting to a Router...
        print('\nscan_and_connect_to_wifi_network(): scanning nets...')
        # Scan for networks:
        nets = self.wlan.scan()
        for net in nets:
            if net.ssid == self.ssid:
                #Connect to router
                connect_to_wifi_network()
                break

    def connect_wpa(self):
        pass
    
    def connect_wpa2(self):
        print('connect_wpa2(): connecting network = ({},{},{})...'.format(self.ssid, WiFiClient.netsec_name(self.netsec), self.password))
        self.wlan.connect(self.ssid, auth=(self.netsec, self.password))

    #Connecting to a WPA2-Enterprise network with EAP-TLS:
    #Copy public and private keys to device /flash/cert.
    #If required to validate server’s public key, an appropriate CA certificate (chain) must also be provided.
    def connect_wpa2_ent(self):
        print('connect_wpa2_ent(): connect using config ({}, {}, {}, {})...'.format(self.ssid, self.netsec, self.identity, self.password))
        self.wlan.connect(ssid=self.ssid, auth=(self.netsec,self.username, self.password), identity=self.identity, ca_certs=self.cacerts, keyfile=self.keyfile, certfile=self.certfile)

    def connect_wep(self):
        pass

    #Connecting with EAP-PEAP or EAP-TTLS (client key and certificate NOT necessary, only a username and password pair)
    #If required to validate server’s public key, an appropriate CA certificate (chain) must also be provided.
    def connect_eap_peap_or_ttls(self):
        pass
        #wlan.connect(ssid=self, auth=(WLAN.WPA2_ENT, self.username, self.password), identity=self.identity, ca_certs=self.ca_certs)
        #self.wlan.connect(ssid=self.ssid, auth=(self.netsec, self.username, self.password), identity=self.identity)


#Assigning a Static IP Address at Boot Up
#Connect to a home router upon boot up, using fixed IP address, use the following script as /flash/boot.py
"""
if machine.reset_cause() != machine.SOFT_RESET:
    wlan.init(mode=WLAN.STA)
    # configuration below MUST match your home router settings!!
    wlan.ifconfig(config=('192.168.178.107', '255.255.255.0', '192.168.178.1', '8.8.8.8'))

if not wlan.isconnected():
    # change the line below to match your network ssid, security and password
    wlan.connect('mywifi', auth=(WLAN.WPA2, 'mywifikey'), timeout=5000)
    while not wlan.isconnected():
        machine.idle() # save power while waiting
"""

#Multiple Networks using a Static IP Address
"""
uart = machine.UART(0, 115200)
os.dupterm(uart)

known_nets = {
    '<net>': {'pwd': '<password>'},
    '<net>': {'pwd': '<password>', 'wlan_config':  ('10.0.0.114', '255.255.0.0', '10.0.0.1', '10.0.0.1')}, # (ip, subnet_mask, gateway, DNS_server)
}

if machine.reset_cause() != machine.SOFT_RESET:
    from network import WLAN
    wl = WLAN()
    wl.mode(WLAN.STA)
    original_ssid = wl.ssid()
    original_auth = wl.auth()

    print("Scanning for known wifi nets")
    available_nets = wl.scan()
    nets = frozenset([e.ssid for e in available_nets])

    known_nets_names = frozenset([key for key in known_nets])
    net_to_use = list(nets & known_nets_names)
    try:
        net_to_use = net_to_use[0]
        net_properties = known_nets[net_to_use]
        pwd = net_properties['pwd']
        sec = [e.sec for e in available_nets if e.ssid == net_to_use][0]
        if 'wlan_config' in net_properties:
            wl.ifconfig(config=net_properties['wlan_config'])
        wl.connect(net_to_use, (sec, pwd), timeout=10000)
        while not wl.isconnected():
            machine.idle() # save power while waiting
        print("Connected to "+net_to_use+" with IP address:" + wl.ifconfig()[0])

    except Exception as e:
        print("Failed to connect to any known network, going into AP mode")
        wl.init(mode=WLAN.AP, ssid=original_ssid, auth=original_auth, channel=6, antenna=WLAN.INT_ANT)
"""