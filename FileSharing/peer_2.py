import sys
import socket
import threading
import time
import pickle
import ast
import numpy as np
import json

from helper_2 import p2p, ServerRunning, Message

HEADERSIZE = 10

class Peer:
    def __init__(self, addr):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.connect((addr, 5000))

        # Second socket for connection between Nodes
        self.p = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.p.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)

        # Third socket for connection between Nodes
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
        self.connection_safe = False

        self.packet_buffer = []
        
        
        self.get_myIP_from_genesis()
        


        c_thred = threading.Thread(target=self.initial_conversation_with_Server_Node)
        c_thred.daemon = True
        c_thred.start()
        
    
        while True:
            if self.gotIP:
                self.get_random_peer_from_genesis()
                self.gotIP = False
            
            if self.first_node == False:
                o_thread = threading.Thread(target=self.connect_to_other_peers)
                o_thread.daemon = True
                o_thread.start()
                self.first_node = True
            
            if self.got_binded:
                # ready to receive connetions from other peers
                r_thread = threading.Thread(target=self.receive_connections)
                i_thread = threading.Thread(target=self.conversation_between_Nodes)
                
                i_thread.start()
                r_thread.start()
                r_thread.join()
                r_thread.join()

            if self.bind:
                self.bind_Peer()
                self.bind = False


    def send_linear_combination_of_packets(self, connection, message):
        """ Send a linear combination of packets to all connected Nodes """
        msg = pickle.dumps(message)
        msg = bytes(f"{len(msg):<{HEADERSIZE}}", 'utf-8')+msg
        connection.send(msg)


    def conversation_between_Nodes(self):
        """ For the connection between the Nodes. 
            Always read the HEADERSIZE which indicates the length of a received 
            packet and read every packet for packet individually.

            Collect packets in a buffer array and send a linear combination of them to all other connected nodes
        """
        message = ""
        packet = "PACKET"
        #packet_number = ""
        #total = ""
        try:
            print("[*] Conversation Ready")
            full_msg = b''
            new_msg = True
            while True:
                msg = self.t.recv(16)
                if new_msg:
                    msglen = int(msg[:HEADERSIZE])
                    new_msg = False
                full_msg += msg

                if len(full_msg)-HEADERSIZE == msglen:
                    message = pickle.loads(full_msg[HEADERSIZE:])
                    new_msg = True
                    full_msg = b''

                    if packet in message:
                        #print(message)
                        #Message.message.append(message)
                        packet_number = message["PACKET"]
                        total = message["GESAMT"]
                        #if len(self.packet_buffer) < total:
                            # Noch nicht alle Packete erhalten, um die Datei wieder herzustellen
                            #self.packet_buffer.append(message)
                        #else:
                            #Message.message = self.packet_buffer
                        Message.message.append(message)
                        print(f"[*] Packet recveived {packet_number+1} / {total}")

                        for p in p2p.connections:
                            self.send_linear_combination_of_packets(p, message)
                            
                        #    msg = pickle.dumps(message)
                        #    msg = bytes(f"{len(msg):<{HEADERSIZE}}", 'utf-8')+msg
                        #    p.send(msg)
                        
        except KeyboardInterrupt:
            self.send_disconnect_to_Node()
            sys.exit()
        except ConnectionResetError:
            self.send_disconnect_to_Node()
            sys.exit()
        except OSError as e:
            pass


    def receive_messages(self, conn, a):
        """ listen constantly for incomming messages 
            (for first node)
        """
        message = ""
        packet = "PACKET"
        try:
            print("[*] Ready to receive messages")
            full_msg = b''
            new_msg = True
            while True:
                msg = conn.recv(16)
                if new_msg:
                    msglen = int(msg[:HEADERSIZE])
                    new_msg = False
                full_msg += msg

                if len(full_msg)-HEADERSIZE == msglen:
                    message = pickle.loads(full_msg[HEADERSIZE:])
                    new_msg = True
                    full_msg = b''
                    
                    # Interpret the message
                    if packet in message:
                        #print("[*] Received Packet")
                        total = message["GESAMT"]
                        packet_number = message["PACKET"]
                        #print(message)
                        #if len(self.packet_buffer) < total:
                            # Noch nicht alle Packete erhalten, um die Datei wieder herzustellen
                         #   self.packet_buffer.append(message)
                        #else:
                        #Message.message = self.packet_buffer
                        Message.message.append(message)
                        print(f"[*] Packet recveived {packet_number} / {total}")
                        # send linear combinations of packets to other Nodes
                    for p in p2p.connections:
                        if p != conn:
                            self.send_linear_combination_of_packets(p, message)
                                #print(f"#Need to send to {conn}")
                                #msg = pickle.dumps(message)
                                #msg = bytes(f"{len(msg):<{HEADERSIZE}}", 'utf-8')+msg
                                #p.send(msg)
        except ConnectionResetError:
            # The connected Peer disconnected himself
            print("[*] Peer diconnected himself")
            self.disconnect(conn, a)
            pass

    def disconnect(self, conn, a):
        """ Disconnect from a Node """
        try:
            self.connections.remove(conn)
            p2p.connections.remove(conn)
            self.peers.remove(a)
            p2p.peers.remove(a)
            conn.close()
            print(f"[*] Disconnected {a}")
        except ValueError:
            pass

    
    def receive_connections(self):
        """ Constantly listen for new incoming connections """
        while True:
            conn, a = self.p.accept()
            self.peers.append(a)
            p2p.peer_list.append(a)
            print(f"[*] New connection from: {a}")
            c_thread = threading.Thread(target=self.receive_messages, args=(conn, a))
            c_thread.daemon = True
            c_thread.start()
            self.connections.append(conn)
            p2p.connections.append(conn)
            print(f"[*] Connected with {a}")
            
            # get data between peers
            self.connection_safe = True


    def get_myIP_from_genesis(self):
        """ Ask the Server what "my" IP is """
        m = "MYIP"
        msg = pickle.dumps(m)
        msg = bytes(f"{len(msg):<{HEADERSIZE}}", 'utf-8')+msg
        self.s.send(msg)
        print("[*] Asked Server for my IP")
        time.sleep(3)
    
    def get_random_peer_from_genesis(self): 
        """ Ask the Server for a random Node """
        m = "req"
        msg = pickle.dumps(m)
        msg = bytes(f"{len(msg):>{HEADERSIZE}}", 'utf-8')+msg
        self.s.send(msg)
        print("[*] Asked Server for random Peers")
        

    def bind_Peer(self):
        """ Bind the Node to the IP Address and 
            listen with socket self.p
        """
        try:
            res = ast.literal_eval(self.myIP[0])
            addr = str(res[0])
            port = res[1]
            self.p.bind((addr, port))  #self.p
            self.p.listen(1)
            print(f"[*] Node IP binded at {port}")
            # ready to connect to other peer 
            self.got_binded = True
        except OSError:
            print("[ERREOOOOORR]")
            return

    def connect_to_other_peers(self):
        """ Send connection to other Node """
        try:
            res = ast.literal_eval(self.peers[0])
            addr = str(res[0])
            port = res[1]
            self.t.connect((addr, port))  # self.t
            p2p.connections.append(self.t) # self.t
            self.connections.append(self.t)
            print(f"[*] Sended Connection to {addr,port}")           
        except OSError as e:
            print(e)
            print("[*] Connection to other peer not possible")
            pass

    def is_pickle(self, data):
        """ Make sure that we receive a pickle object"""
        try:
            pickle.loads(data)
            return True
        except (pickle.UnpicklingError, AttributeError, EOFError, ImportError,IndexError):
            return False
        
    def initial_conversation_with_Server_Node(self):
        """ Handle the initial conversation between the Node and the Server.
            Connect to the server, ask him for a random node and own IP Address, disconnect from the Server
            and connect to the random Node.

            If this is the first node in the Network, then this is also the connection for receiving packets
            between the (first) Node and the Server
        """
        random_peer = "RANDOM_PEER"
        packet = "PACKET"
        myip = "YOURIP"
        first = "FIRST"
        message = ""
        try:
            full_msg = b''
            new_msg = True
            while True:
                msg = self.s.recv(16)
                if new_msg:
                    msglen = int(msg[:HEADERSIZE])
                    new_msg = False
                full_msg += msg
                    
                if len(full_msg)-HEADERSIZE == msglen:
                    message = pickle.loads(full_msg[HEADERSIZE:])
                    new_msg = True
                    full_msg = b''
                    
                    ## Interpret the message
                    if random_peer in message:
                        # Get some random Peer from the Server Node
                        print(f"[*] Got some random peer {message[12:]}")
                        # Message looks like: 'RANDOM_PEER|(127.0.0.1,3000)
                        self.peers.append(message[12:])
                        p2p.peer_list.append(message[12:])
                        # disconnect from the genesis Node
                        self.send_disconnet_to_server()
                        print("[*] Disconnect from Server")
                        self.bind = True
                        self.first_node = False
                        #self.new_socket = self.s.dup()
                        #self.connect_to_other_peers()
                    elif myip in message:
                        # Now I know me IP address and Port
                        print(f"[*] My Adress is: {message[7:]}")
                        self.myIP.append(message[7:])
                        self.gotIP = True
                    elif first in message:
                        # The first node in the network, so stay connected to the Server (Genesis) Node
                        print("[*] First Node in the Network")
                        self.bind = True
                        self.first_node = True
                        p2p.connections.append(self.s)
                    elif packet in message:
                        # got some packets from other peers
                        #print(message)
                        Message.message.append(message)
                        for p in p2p.connections:
                            self.send_linear_combination_of_packets(p, message)
        except KeyboardInterrupt:
            self.send_disconnet_to_server()
            sys.exit()
        except ConnectionResetError:
            self.send_disconnet_to_server()
            sys.exit()
        except OSError:
            pass
        except ValueError:
            pass

    def send_disconnect_to_Node(self):
        try:
            m = "disconnect"
            msg = pickle.dumps(m)
            msg = bytes(f"{len(msg):<{HEADERSIZE}}", 'utf-8')+msg
            self.p.send(msg)
        except OSError:
            # TODO: Remove connections ?
            print("[*] Node disconnected")
        
    def send_disconnet_to_server(self):
        """Send disconnection signal to the server Node"""
        try:
            m = "disconnect"
            msg = pickle.dumps(m)
            msg = bytes(f"{len(msg):<{HEADERSIZE}}", 'utf-8')+msg
            self.s.send(msg)
        except ConnectionResetError:
            # Server is disconneted
            # TODO: Become the Server
            print("[*] Server disconnected from the Network")