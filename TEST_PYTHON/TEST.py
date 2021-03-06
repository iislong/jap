from twisted.internet import protocol, reactor, tcp
from twisted.internet.abstract import isIPAddress, isIPv6Address
import base64
import struct
import json
import socket
import logging

class TunnelProtocol(protocol.Protocol):
    def __init__(self):
        logger.debug("TunnelProtocol.__init__")
        
        self.tunnelOutputProtocol = None
        self.tunnelOutputProtocolFactory = None
        
    def connectionMade(self):
        logger.debug("TunnelProtocol.connectionMade")
        
        if self.factory.configuration["PROXY_SERVERS"][self.factory.i]["TYPE"] == "HTTP":
            self.tunnelOutputProtocolFactory = HTTPTunnelOutputProtocolFactory(self.factory.i, self.factory.configuration, self.factory.address, self.factory.port, self)
            self.tunnelOutputProtocolFactory.protocol = HTTPTunnelOutputProtocol
        else:
            if self.factory.configuration["PROXY_SERVERS"][self.factory.i]["TYPE"] == "SOCKS5":
                self.tunnelOutputProtocolFactory = SOCKS5TunnelOutputProtocolFactory(self.factory.i, self.factory.configuration, self.factory.address, self.factory.port, self)
                self.tunnelOutputProtocolFactory.protocol = SOCKS5TunnelOutputProtocol
            else:
                self.transport.loseConnection()
                return
        
        self.tunnelOutputProtocol = self.tunnelOutputProtocolFactory.buildProtocol(self.transport.getPeer())
        self.tunnelOutputProtocol.makeConnection(self.transport)
        
    def connectionLost(self, reason):
        logger.debug("TunnelProtocol.connectionLost")
        
        if self.tunnelOutputProtocol is not None:
            self.tunnelOutputProtocol.connectionLost(reason)
        else:
            if self.factory.outputProtocol is not None:
                self.factory.outputProtocol.connectionLost(reason)
    
    def dataReceived(self, data):
        logger.debug("TunnelProtocol.dataReceived")
        
        if self.tunnelOutputProtocol is not None:
            self.tunnelOutputProtocol.dataReceived(data)
        else:
            if self.factory.outputProtocol is not None:
                self.factory.outputProtocol.dataReceived(data)
    
    def tunnelOutputProtocol_connectionMade(self, data):
        logger.debug("TunnelProtocol.tunnelOutputProtocol_connectionMade")
        
        self.tunnelOutputProtocol = None
        
        if self.factory.contextFactory is not None:
            self.transport.startTLS(self.factory.contextFactory)
        
        self.factory.outputProtocol = self.factory.outputProtocolFactory.buildProtocol(self.transport.getPeer())
        self.factory.outputProtocol.makeConnection(self.transport)
        
        if len(data) > 0:
            self.factory.outputProtocol.dataReceived(data)

class TunnelProtocolFactory(protocol.ClientFactory):
    def __init__(self, i, configuration, address, port, outputProtocolFactory, contextFactory=None, timeout=30, bindAddress=None):
        logger.debug("TunnelProtocolFactory.__init__")
        
        self.i = i
        self.configuration = configuration
        self.address = address
        self.port = port
        self.outputProtocol = None
        self.outputProtocolFactory = outputProtocolFactory
        self.contextFactory = contextFactory
        self.timeout = timeout
        self.bindAddress = bindAddress
    
    def startedConnecting(self, connector):
        logger.debug("TunnelProtocolFactory.startedConnecting")
        
        self.outputProtocolFactory.startedConnecting(connector)
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("TunnelProtocolFactory.clientConnectionFailed")
        
        self.outputProtocolFactory.clientConnectionFailed(connector, reason)
    
    def clientConnectionLost(self, connector, reason):
        logger.debug("TunnelProtocolFactory.clientConnectionLost")
        
        if self.outputProtocol is None:
            self.outputProtocolFactory.clientConnectionFailed(connector, reason)
        else:
            self.outputProtocolFactory.clientConnectionLost(connector, reason)

class Tunnel(object):
    def __init__(self, configuration):
        logger.debug("Tunnel.__init__")
        
        self.configuration = configuration
    
    def connect(self, address, port, outputProtocolFactory, contextFactory=None, timeout=30, bindAddress=None):
        logger.debug("Tunnel.connect")
        
        if len(self.configuration["PROXY_SERVERS"]) == 0:
            if contextFactory is None:
                return reactor.connectTCP(address, port, outputProtocolFactory, timeout, bindAddress)
            else:
                return reactor.connectSSL(address, port, outputProtocolFactory, contextFactory, timeout, bindAddress)
        else:
            i = len(self.configuration["PROXY_SERVERS"])
            
            tunnelProtocolFactory = TunnelProtocolFactory(i - 1, self.configuration, address, port, outputProtocolFactory, contextFactory, timeout, bindAddress)
            tunnelProtocolFactory.protocol = TunnelProtocol
            
            i = i - 1
            
            while i > 0:
                tunnelProtocolFactory = TunnelProtocolFactory(i - 1, self.configuration, self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"], tunnelProtocolFactory, contextFactory, timeout, bindAddress)
                tunnelProtocolFactory.protocol = TunnelProtocol
                
                i = i - 1
            
            return reactor.connectTCP(self.configuration["PROXY_SERVERS"][i]["ADDRESS"], self.configuration["PROXY_SERVERS"][i]["PORT"], tunnelProtocolFactory, timeout, bindAddress)

class HTTPTunnelOutputProtocol(protocol.Protocol):
    def __init__(self):
        logger.debug("HTTPTunnelOutputProtocol.__init__")
        
        self.data = ""
        self.dataState = 0
        
    def connectionMade(self):
        logger.debug("HTTPTunnelOutputProtocol.connectionMade")
        
        request = "CONNECT " + str(self.factory.address) + ":" + str(self.factory.port) + " HTTP/1.0\r\n"
        
        if self.factory.configuration["PROXY_SERVERS"][self.factory.i]["AUTHENTICATION"]["USERNAME"] != "":
            request = request + "Proxy-Authorization: Basic " + base64.standard_b64encode(self.factory.configuration["PROXY_SERVERS"][self.factory.i]["AUTHENTICATION"]["USERNAME"] + ":" + self.factory.configuration["PROXY_SERVERS"][self.factory.i]["AUTHENTICATION"]["PASSWORD"]) + "\r\n"
        
        request = request + "\r\n"
        
        self.transport.write(request)
        
    def connectionLost(self, reason):
        logger.debug("HTTPTunnelOutputProtocol.connectionLost")
    
    def dataReceived(self, data):
        logger.debug("HTTPTunnelOutputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            self.processDataState0()
            return
    
    def processDataState0(self):
        logger.debug("HTTPTunnelOutputProtocol.processDataState0")
        
        i = self.data.find("\r\n\r\n")
        
        if i == -1:
            return
            
        i = i + 4
        
        dataLines = self.data[:i].split("\r\n")
        dataLine0 = dataLines[0]
        dataLine0Values = dataLine0.split(" ", 2)
        
        if len(dataLine0Values) != 3:
            self.transport.loseConnection()
            return
        
        if dataLine0Values[1] != "200":
            self.transport.loseConnection()
            return
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(self.data[i:])
        
        self.data = ""
        self.dataState = 1

class HTTPTunnelOutputProtocolFactory(protocol.ClientFactory):
    def __init__(self, i, configuration, address, port, tunnelProtocol):
        logger.debug("HTTPTunnelOutputProtocolFactory.__init__")
        
        self.i = i
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnelProtocol = tunnelProtocol
    
    def startedConnecting(self, connector):
        logger.debug("HTTPTunnelOutputProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("HTTPTunnelOutputProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        logger.debug("HTTPTunnelOutputProtocolFactory.clientConnectionLost")

class SOCKS5TunnelOutputProtocol(protocol.Protocol):
    def __init__(self):
        logger.debug("SOCKS5TunnelOutputProtocol.__init__")
        
        self.data = ""
        self.dataState = 0
    
    def connectionMade(self):
        logger.debug("SOCKS5TunnelOutputProtocol.connectionMade")
        
        request = struct.pack("!BBB", 0x05, 0x01, 0x00)
        
        self.transport.write(request)
    
    def connectionLost(self, reason):
        logger.debug("SOCKS5TunnelOutputProtocol.connectionLost")
    
    def dataReceived(self, data):
        logger.debug("SOCKS5TunnelOutputProtocol.dataReceived")
        
        self.data = self.data + data
        if self.dataState == 0:
            self.processDataState0()
            return
        
        if self.dataState == 1:
            self.processDataState1()
            return
    
    def processDataState0(self):
        logger.debug("SOCKS5TunnelOutputProtocol.processDataState0")
        
        if len(self.data) < 2:
            return
        
        if ord(self.data[0]) != 0x05:
            self.transport.loseConnection()
            return
        
        addressType = 0x03
        if isIPAddress(self.factory.address) == True:
            addressType = 0x01
        else:
            if isIPv6Address(self.factory.address) == True:
                addressType = 0x04
        
        request = struct.pack("!BBB", 0x05, 0x01, 0x00)
        
        if addressType == 0x01:
            address = struct.unpack("!I", socket.inet_aton(self.factory.address))[0]
            request = request + struct.pack("!BI", 0x01, address)
        else:
            if addressType == 0x03:
                address = str(self.factory.address)
                addressLength = len(address)
                request = request + struct.pack("!BB%ds" % addressLength, 0x03, addressLength, address)
            else:
                self.transport.loseConnection()
                return
        
        request = request + struct.pack("!H", self.factory.port)
        
        self.transport.write(request)
        
        self.data = ""
        self.dataState = 1
    
    def processDataState1(self):
        logger.debug("SOCKS5TunnelOutputProtocol.processDataState1")
        
        if len(self.data) < 10:
            return
        
        if ord(self.data[0]) != 0x05:
            self.transport.loseConnection()
            return
        
        if ord(self.data[1]) != 0x00:
            self.transport.loseConnection()
            return
        
        self.factory.tunnelProtocol.tunnelOutputProtocol_connectionMade(self.data[10:])
        
        self.data = ""
        self.dataState = 2

class SOCKS5TunnelOutputProtocolFactory(protocol.ClientFactory):
    def __init__(self, i, configuration, address, port, tunnelProtocol):
        logger.debug("SOCKS5TunnelOutputProtocolFactory.__init__")
        
        self.i = i
        self.configuration = configuration
        self.address = address
        self.port = port
        self.tunnelProtocol = tunnelProtocol
    
    def startedConnecting(self, connector):
        logger.debug("SOCKS5TunnelOutputProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("SOCKS5TunnelOutputProtocolFactory.clientConnectionFailed")
    
    def clientConnectionLost(self, connector, reason):
        logger.debug("SOCKS5TunnelOutputProtocolFactory.clientConnectionLost")

class TestProtocol(protocol.Protocol):
    def __init__(self):
        logger.debug("TestProtocol.__init__")
        self.data = ""
        self.dataState = 0
        
    def connectionMade(self):
        logger.debug("TestProtocol.connectionMade")
        
        self.transport.write("HEAD / HTTP/1.1\r\n")
        self.transport.write("Host: www.google.com\r\n")
        self.transport.write("\r\n")
    
    def connectionLost(self, reason):
        logger.debug("TestProtocol.connectionLost")
        
        if self.dataState == 0:
            self.factory.test.test_NOT_OK()
        
    def dataReceived(self, data):
        logger.debug("TestProtocol.dataReceived")
        
        self.data = self.data + data
        
        i = self.data.find("\r\n\r\n")
        
        if i == -1:
            return
        
        i = i + 4
        
        self.dataState = 1
        print self.data
        dataLines = self.data[:i].split("\r\n")
        dataLine0 = dataLines[0]
        dataLine0Values = dataLine0.split(" ", 2)
        
        if len(dataLine0Values) != 3:
            self.factory.test.test_NOT_OK()
            
            self.transport.loseConnection()
            return
        
        if dataLine0Values[1] not in ["200", "300", "301", "302", "303", "304", "305", "306", "307"]:
            self.factory.test.test_NOT_OK()
            
            self.transport.loseConnection()
            return
        
        self.factory.test.test_OK()
        
        self.transport.loseConnection()
        
class TestProtocolFactory(protocol.ClientFactory):
    def __init__(self):
        logger.debug("TestProtocolFactory.__init__")
        
        self.test = None
    
    def startedConnecting(self, connector):
        logger.debug("TestProtocolFactory.startedConnecting")
    
    def clientConnectionFailed(self, connector, reason):
        logger.debug("TestProtocolFactory.clientConnectionFailed")
        
        self.test.test_NOT_OK()
    
    def clientConnectionLost(self, connector, reason):
        logger.debug("TestProtocolFactory.clientConnectionLost")

class Test(object):
    def __init__(self, configuration):
        logger.debug("Test.__init__")
        
        self.configuration = configuration
    
    def test_OK(self):
        logger.debug("Test.test_OK")
        
        logger.info("test OK")
        
        reactor.stop()
        
    def test_NOT_OK(self):
        logger.debug("Test.test_NOT_OK")
        
        logger.info("test NOT OK")
        
        reactor.stop()
    
    def test(self):
        logger.debug("Test.test")
        
        testProtocolFactory = TestProtocolFactory()
        testProtocolFactory.protocol = TestProtocol
        testProtocolFactory.test = self
        
        tunnel = Tunnel(self.configuration)
        tunnel.connect("www.google.com", 80, testProtocolFactory)

configuration = json.load(open("TEST.json"))

logging.basicConfig()
logger = logging.getLogger("TEST")

if configuration["LOGGER"]["LEVEL"] == "DEBUG":
    logger.setLevel(logging.DEBUG)
elif configuration["LOGGER"]["LEVEL"] == "INFO":
    logger.setLevel(logging.INFO)
elif configuration["LOGGER"]["LEVEL"] == "WARNING":
    logger.setLevel(logging.WARNING)
elif configuration["LOGGER"]["LEVEL"] == "ERROR":
    logger.setLevel(logging.ERROR)
elif configuration["LOGGER"]["LEVEL"] == "CRITICAL":
    logger.setLevel(logging.CRITICAL)
else:
    logger.setLevel(logging.NOTSET)

test = Test(configuration)

reactor.callFromThread(test.test)
reactor.run()