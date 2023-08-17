import socket
import threading
import pickle
import random
import numpy as np

from helper_2 import ServerRunning, p2p, Message

HEADERSIZE = 10

class StartGenesisNode:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('127.0.0.1', 5000))
        self.s.listen(3)

        self.peers = []
        self.connections = []

        print("[*] Server Node Started")
        print("[*] Waiting for connections...")

        ServerRunning.isRunning = True

        while True:
            conn, a = self.s.accept()
            thread = threading.Thread(target=self.handle, args=(conn,a))
            thread.daemon = True
            thread.start()
            self.connections.append(conn)
            p2p.connections.append(conn)
            p2p.peer_list.append(a)
            self.peers.append(a)
            print(f"Got connection from {a}")
            #p2p.peer_list.append(a)
    
    def is_pickle(self, data):
        try:
            pickle.loads(data)
            return True
        except (pickle.UnpicklingError, AttributeError, EOFError, ImportError,IndexError):
            return False
            
    def handle(self, c, a):
        req = "req"
        myip = "MYIP"
        disconnect = "disconnect"
        message = ""
        packet = "PACKET"
        try:
            full_msg = b''
            new_msg = True
            while True:
                msg = c.recv(16)
                if new_msg:
                    msglen = int(msg[:HEADERSIZE])
                    new_msg = False
                full_msg += msg

                if len(full_msg)-HEADERSIZE == msglen:
                    message = pickle.loads(full_msg[HEADERSIZE:])
                    #print(message)
                    new_msg = True
                    full_msg = b''

                    # Interpret message
                    if req in message:
                        # Peers asks for some random peers
                        # Remove the peer that just connected from the list
                        # So that it not get's it's own address
                        tmp = list(filter(lambda x: x != a, self.peers))
                        #print(f"tmp: {tmp}")
                        if len(tmp) == 0: # First Peer in to connect to the network, so no peers to share
                            m1 = "FIRST"
                            m = pickle.dumps(m1)
                            m = bytes(f"{len(m):<{HEADERSIZE}}", 'utf-8')+m
                            c.send(m) #conn.send(m)
                        else:
                            # Send one Random Peer
                            # The Peer then connects to the list of that random peer
                            r = random.choice(tmp)
                            m1 = "RANDOM_PEER"+ "|" + str(r)
                            m = pickle.dumps(m1)
                            m = bytes(f"{len(m):<{HEADERSIZE}}", 'utf-8')+m
                            c.send(m) #conn.send(m)
                    elif myip in message:
                        # Tell the Peer his IP
                        m1 = "YOURIP" + "|" + str(a)
                        m = pickle.dumps(m1)
                        m = bytes(f"{len(m):<{HEADERSIZE}}", 'utf-8')+m
                        c.send(m) #conn.send(m)
                    elif packet in message:
                        #print("[*] Packet Received")
                        Message.message.append(message)
                        packet_number = message["PACKET"]
                        total = message["GESAMT"]
                        print(f"[*] Packet recveived {packet_number+1} / {total}")
                    elif disconnect in message:
                        self.disconnect_peer(c, a)
                        break
            """while True:
                data = c.recv(1024)
                #print(f"#### {data}")
                #for conn in self.connections:
                # Check if we get a list with pickle structure
                if self.is_pickle(data) == True:
                    d = pickle.loads(data)
                    matrix = np.array(d["matrix"])
                    packet = d["encoded_packet"]
                    c1 = d["c1"]
                    key = d["key"]
                    q = d["q"]
                    print(f"matrix: {matrix}, packet: {packet}, c1: {c1}, key: {key}, q: {q}")
                elif data and data.decode('utf-8') == "req":
                    # Peers asks for some random peers
                    # Remove the peer that just connected from the list
                    # So that it not get's it's own address
                    tmp = list(filter(lambda x: x != a, self.peers))
                    #print(f"tmp: {tmp}")
                    if len(tmp) == 0: # First Peer in to connect to the network, so no peers to share
                        m1 = "FIRST"
                        m = pickle.dumps(m1)
                        m = bytes(f"{len(m):<{HEADERSIZE}}", 'utf-8')+m
                        c.send(m) #conn.send(m)
                    else:
                        # Send one Random Peer
                        # The Peer then connects to the list of that random peer
                        r = random.choice(tmp)
                        m1 = "RANDOM_PEER"+ "|" + str(r)
                        m = pickle.dumps(m1)
                        m = bytes(f"{len(m):<{HEADERSIZE}}", 'utf-8')+m
                        c.send(m) #conn.send(m)
                elif data and data.decode('utf-8') == "MYIP":
                    # Tell the Peer his IP
                    m1 = "YOURIP" + "|" + str(a)
                    m = pickle.dumps(m1)
                    m = bytes(f"{len(m):<{HEADERSIZE}}", 'utf-8')+m
                    c.send(m) #conn.send(m)
                elif data and data.decode('utf-8') == "disconnect":
                    self.disconnect_peer(c, a)
                    break"""
        except ConnectionResetError:
            self.disconnect(c, a)
        except OSError:
            self.disconnect_peer(c, a)
        except ValueError:
            pass
                    
    def disconnect_peer(self, c, a):
        """Disconnect a new node after it got a random Node from the network"""
        try:
            self.connections.remove(c)
            p2p.connections.remove(c)
            c.close()
            print(f"[*] Disconnected Peer {a}")
        except ValueError:
            return

    def disconnect(self, c, a):
        try:
            self.connections.remove(c)
            p2p.connections.remove(c)
            p2p.peers.remove(c)
            self.peers.remove(a)
            c.close()
            print(f"Disconnected Peer {a}")
            # update peer list
            #self.sendPeers()
        except ValueError:
            pass



    def sendPeers(self):
        for conn in self.connections:
            m = pickle.dumps(self.peers)
            conn.send(m)