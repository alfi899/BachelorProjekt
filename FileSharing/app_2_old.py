import sys
import socket
import threading
import time
import pickle
import random
import ast


class ServerRunning:
    isRunning = False

class p2p:
    peer_list = ['127.0.0.1']
    peers = []
    connections = []

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
            self.peers.append(a)
            print(f"Got connection from {a}")
            #p2p.peer_list.append(a)
            
    def handle(self, c, a):
        try:
            while True:
                data = c.recv(1024)
                #print(f"#### {data}")
                for conn in self.connections:
                    if data and data.decode('utf-8') == "req":
                        # Peers asks for some random peers
                        # Remove the peer that just connected from the list
                        # So that it not get's it's own address
                        tmp = list(filter(lambda x: x != a, self.peers))
                        #print(f"tmp: {tmp}")
                        if len(tmp) == 0: # First Peer in to connect to the network, so no peers to share
                            m1 = "FIRST"
                            m = pickle.dumps(m1)
                            conn.send(m)
                        else:
                            # Send one Random Peer
                            # The Peer then connects to the list of that random peer
                            r = random.choice(tmp)
                            m1 = "RANDOM_PEER"+ "|" + str(r)
                            m = pickle.dumps(m1)
                            conn.send(m)
                    elif data and data.decode('utf-8') == "MYIP":
                        # Tell the Peer his IP
                        m1 = "YOURIP" + "|" + str(a)
                        m = pickle.dumps(m1)
                        conn.send(m)
                    elif data and data.decode('utf-8') == "disconnect":
                        self.disconnect_peer(c, a)
                        break
        except ConnectionResetError:
            self.disconnect(c, a)
        except OSError:
            self.disconnect_peer(c, a)
                    
    def disconnect_peer(self, c, a):
        """Disconnect a new node after it got a random Node from the network"""
        try:
            self.connections.remove(c)
            c.close()
            print(f"[*] Disconnected Peer {a}")
        except ValueError:
            return

    def disconnect(self, c, a):
        self.connections.remove(c)
        p2p.connections.remove(c)
        p2p.peers.remove(c)
        self.peers.remove(a)
        c.close()
        print(f"Disconnected Peer {a}")
        # update peer list
        self.sendPeers()



    def sendPeers(self):
        for conn in self.connections:
            m = pickle.dumps(self.peers)
            conn.send(m)


class Peer:
    def __init__(self, addr):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.connect((addr, 5000))

        # Second socket for connection between peers
        self.p = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.p.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)

        # Third socket for testing purpose
        self.t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


        self.peers = []
        self.first_peer = []
        self.connections = []
        self.myIP = []
        self.gotIP = False
        self.got_peer = False
        self.bind = False
        self.connect_to_peer = False
        self.first_node = None
        self.got_binded = False
        
        
        self.get_myIP_from_genesis()
        


        c_thred = threading.Thread(target=self.initial_conversation_with_Server_Node)
        c_thred.daemon = True
        c_thred.start()
        
    
        while True:
            if self.gotIP:
                self.get_random_peer_from_genesis()
                self.gotIP = False
                
            if self.bind:
                self.bind_Peer()
                self.bind = False
            
            if self.first_node == False:
                print("HEEEEEEERRRRR")
                o_thread = threading.Thread(target=self.connect_to_other_peers)
                o_thread.daemon = True
                o_thread.start()
                #self.connect_to_other_peers()
                self.first_node = True

            
            if self.got_binded:
                # ready to receive connetions from other peers
                r_thread = threading.Thread(target=self.receive_connections)
                r_thread.start()
                r_thread.join()

                #i_thread = threading.Thread(target=self.receive_messages)
                #i_thread.start()
                #i_thread.join()

    def receive_messages(self, conn, a):
        # listen constantly for incomming messages
        try:
            print("[*] Ready to receive Messages")
            data = conn.recv(1024)
            if data:
                # Check if we get a list with pickle structure
                if self.is_pickle(data) == True:
                    d = pickle.loads(data)
                    print(f">>> {d}")
                else:
                    print(f">>> {data.decode('utf-8')}")
        except:
            # The connected Peer disconnected himself
            self.disconnect(conn, a)
            pass
    
    def send_message_to_peers(self):
        self.t.send("Test Message".encode('utf-8'))

    def disconnect(self, conn, a):
        self.connections.remove(conn)
        self.peers.remove(a)
        conn.close()
        print(f"[*] Disconnected {a}")

    def receive_connections(self):
        # constantly listen for connetions
        while True:
            conn, a = self.p.accept()
            self.peers.append(a)
            print(f"[*] New connection from: {a}")

            c_thread = threading.Thread(target=self.receive_messages, args=(conn, a))
            c_thread.daemon = True
            c_thread.start()
            self.connections.append(conn)
            print(f"[*] Connected with {a}")

    def get_myIP_from_genesis(self):
        # Ask the server, what "My" Ip is
        self.s.send("MYIP".encode('utf-8'))
        print("[*] Asked Server for my IP")
        time.sleep(3)
    
    def get_random_peer_from_genesis(self): 
        # send request to get random Peers
        self.s.send("req".encode('utf-8'))
        print("[*] Asked Server for random Peers")
        #if len(self.peers) == 1:
        #    self.connect_to_other_peers

    def bind_Peer(self):
        """Listen with socket self.p
        """
        try:
            res = ast.literal_eval(self.myIP[0])
            addr = str(res[0])
            port = res[1]
            #print(f"addr: {addr}, port:{port}")
            self.p.bind((addr, port))
            self.p.listen(3)
            print(f"[*] Node IP binded")
            # ready to connect to other peer 
            self.got_binded = True
        except OSError:
            print("[ERREOOOOORR]")
            return

    def connect_to_other_peers(self):
        # Connect to the peer
        try:
            res = ast.literal_eval(self.peers[0])
            addr = str(res[0])
            port = res[1]
            self.t.connect((addr, port))
            print(f"[*] Sended Connection to {addr,port}")           
        except OSError:
            print("[*] Connection to other peer not possible")
            pass

    def is_pickle(self, data):
        try:
            pickle.loads(data)
            return True
        except (pickle.UnpicklingError, AttributeError, EOFError, ImportError,IndexError):
            return False
        
    def initial_conversation_with_Server_Node(self):
        random_peer = "RANDOM_PEER"
        get_connections = "CONNECTIONS"
        myip = "YOURIP"
        first = "FIRST"
        try:
            while True:
                data = self.s.recv(1024)
                if data:
                    # Check if we get a list with pickle structure
                    if self.is_pickle(data) == True:
                        d = pickle.loads(data)
                        #print(f">>> {d}")
                        if random_peer in d:
                            # Get some random Peer from the Server Node
                            print(f"[*] Got some random peer {d[12:]}")
                            # Message looks like: 'RANDOM_PEER|(127.0.0.1,3000)
                            self.peers.append(d[12:])
                            #self.got_peer = True
                            # disconnect from the genesis Node
                            self.send_disconnet_to_server()
                            print("[*] Disconnect from Server")
                            self.bind = True
                            self.first_node = False
                            self.s.close()
                            #self.connect_to_other_peers()
                        elif myip in d:
                            # Now I know me IP address and Port
                            print(f"[*] My Adress is: {d[7:]}")
                            self.myIP.append(d[7:])
                            self.gotIP = True
                        elif first in d:
                            # The first node in the network, so stay connected to the Server (Genesis) Node
                            print("[*] First Node in the Network")
                            self.bind = True
                            self.first_node = True
                            return
                    elif get_connections in d:
                        # Got a Connection List from another Peer
                        print(f"GOT CONNECTION LIST {d}")
        except KeyboardInterrupt:
            self.send_disconnet_to_server()
            sys.exit()
        except ConnectionResetError:
            self.send_disconnet_to_server()
            sys.exit()
        except OSError:
            pass

    def send_disconnect_to_Node(self):
        self.p.send("disconnect".encode('utf-8'))

    def send_disconnet_to_server(self):
        """Send disconnection signal to the server Node"""
        # From server
        self.s.send("disconnect".encode('utf-8'))
        self.s.close()

def background():
    print("[*] Connecting to the Network")
    # Start Genisis Node (Server)
    time.sleep(3)
    try:
        try:
            Peer('127.0.0.1')
        except:
            if ServerRunning.isRunning == False:
                StartGenesisNode()
    except KeyboardInterrupt:
        sys.exit()

if __name__ == "__main__":
    background()
