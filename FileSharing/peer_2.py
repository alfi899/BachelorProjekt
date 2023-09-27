import sys
import socket
import threading
import time
import pickle
import ast
import numpy as np
import json
import sympy
import itertools
import random

from helper_2 import p2p, ServerRunning, Message
from elgamal_encryption_2 import Gamal

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

        self.elgamal = Gamal()

        self.matrix = []

        
        
        self.get_myIP_from_genesis()
        #self.tell_server_my_public_key()
        


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


    def recalculate_result(self, lc, matrix, p):
        dec = [self.elgamal.decryption(lc[i][0], lc[i][1], Message.key) for i in range(len(lc))]
        
        print("DEC: ", dec)
        m = sympy.Matrix(matrix)
        q = (p-1) // 2
        matrix_inverse = m.inv_mod(q)
        print("INVERSE Matrix: ", matrix_inverse)

        X = self.calculate_results(dec, matrix_inverse, p)

        return X
    

    def calculate_results(self, lc_list, B, p):
        final_res = []

        # Use np matrix, better for zugriff
        mat = np.array(B)
        for i in range(0, len(lc_list)):
            res = []
            for j in range(0, len(lc_list)):
                r = [sympy.Pow(x, mat[i][j]) % p for x in lc_list[j]]
                res.append(r)
            t = res[0]
            result = []
            for sublist in res[1:]:
                t = [(a * b) % p for a,b in zip(t, sublist)]
            t = [p - x if x > 256 else x for x in t] # Sometimes the bigger values are represented
            result.append(t)
            result = list(itertools.chain.from_iterable(result))
            final_res.append(result)
        return final_res


    def conversation_between_Nodes(self):
        """ For the connection between the Nodes. 
            Always read the HEADERSIZE which indicates the length of a received 
            packet and read every packet for packet individually.
        """
        message = ""
        packet = "PACKET"
        disconnect = "disconnect"
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
                        print(message)
                        self.matrix.append(message['exponentes'])
                        self.packet_buffer.append(message['PACKET'])
                        print(f"[*] Packets comming from {self.t.getpeername()}")
                        Message.key = message['key']
                        Message.p = message['p']
                        Message.format = message['format']
                        # send linear combinations to other peers
                        serialized_message = pickle.dumps(message)
                        serialized_message = bytes(f"{len(serialized_message):<{HEADERSIZE}}", 'utf-8')+serialized_message
                        #for p in p2p.connections:
                        #    p.send(serialized_message)
                        lenght = message['L']
                        ma = np.array(self.matrix)
                        rank = np.linalg.matrix_rank(ma)
                        q = (Message.p - 1) // 2
                        if rank % q == lenght:
                            # ready to decrypt the linear combinations
                            print("LC_list", self.packet_buffer)
                            Message.message = self.recalculate_result(self.packet_buffer, self.matrix, Message.p)
                            Message.message_ready = True
                            #self.packet_buffer = []
                    # if node disconnected from the Network, tell it the other ones
                    if disconnect in message:
                        for p in p2p.connections:
                            print(f"I am Here and neet to tell {p} that ?? has disconnected")        
        except KeyboardInterrupt:
            print("[********] Disconnect")
            self.send_disconnect_to_Node()
            self.send_disconnet_to_server()
            sys.exit()
        except ConnectionResetError:
            self.send_disconnect_to_Node()
            self.send_disconnet_to_server()
            sys.exit()
        except OSError as e:
            pass

    def tell_disconnection(self, conn, addr):
        """ Tell the the connected nodes, that a Node has disconnected to the network """
        pass


    def receive_messages(self, conn, a):
        """ listen constantly for incomming messages """
        message = ""
        packet = "PACKET"
        disconnect = "disconnect"
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
                        print(message)
                        self.matrix.append(message['exponentes'])
                        self.packet_buffer.append(message['PACKET'])
                        print(f"[*] Packets comming from {conn.getpeername()}")
                        Message.key = message['key']
                        Message.p = message['p']
                        Message.format = message['format']
                        # send linear combinations to other peers
                        serialized_message = pickle.dumps(message)
                        serialized_message = bytes(f"{len(serialized_message):<{HEADERSIZE}}", 'utf-8')+serialized_message
                        #for p in p2p.connections:
                        #    p.send(serialized_message)
                        lenght = message['L']
                        ma = np.array(self.matrix)
                        rank = np.linalg.matrix_rank(ma)
                        q = (Message.p - 1) // 2
                        if rank % q == lenght:
                            # ready to decrypt the linear combinations
                            print("LC_list", self.packet_buffer)
                            Message.message = self.recalculate_result(self.packet_buffer, self.matrix, Message.p)
                            Message.message_ready = True
                            #self.packet_buffer = []
                    # if node disconnected from the Network, tell it the other ones
                    elif disconnect in message:
                        for p in p2p.connections:
                            print(f"I am Here and neet to tell {p} that {conn} has disconnected")
                            
        except ConnectionResetError:
            # The connected Peer disconnected himself
            print("[***] Peer diconnected himself")
            self.disconnect(conn, a)
            #pass
        except KeyboardInterrupt:
            print("[*] Disconnect from the Network--")
            sys.exit()

    def disconnect(self, conn, a):
        """ Disconnect from a Node """
        try:
            self.connections.remove(conn)
            p2p.connections.remove(conn)
            self.peers.remove(a)
            p2p.peers.remove(a)
            #conn.close()
            print(f"[*] Disconnected {a}")
        except ValueError:
            print("[*] Tell neighbor nodes from disconnection")
            #for p in p2p.connections:
            #    m = f"disconnect {conn}"
            #    msg = pickle.dumps(m)
            #    msg = bytes(f"{len(msg):<{HEADERSIZE}}", 'utf-8')+msg
            #    p.send(msg)
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

    def tell_server_my_public_key(self):
        """ Tell the other Peer (if first Node => Server Node) my public key for 
            encryption with elgamal
        """
        pk = self.elgamal.h # public key
        q = self.elgamal.q
        g = self.elgamal.g
        m = {"public_key": pk, "q": q, "g": g}
        msg = pickle.dumps(m)
        msg = bytes(f"{len(msg):>{HEADERSIZE}}", 'utf-8')+msg
        self.s.send(msg)
        print("[*] Senden Public Key to Server")
        

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
    
    def compute_linear_combinations(self, packet_list):
            """ Compute the linear combinations of the elcrypted elgamal packages.
                (It only computes one linear combination)

                1. Take every element exp() from the message list
                   [list1, list2, list3] => [list1^a, list2^b, list3^c], where a,b,c are in the exponents list

                2. Compute the c1 linear combinations 
                   c1_1^a * c1_2^b * c1_3^c * .. * c1_n*n 
            
                3. Compute the linear combination of the c2 list's. Like element-wise list multiplication, with the earlier 
                   modified exponential list
            """
            exp_list = []
            e = []
            c1 = 1
            p = self.elgamal.p
            for i in range(0, len(packet_list)):
                r = random.randint(2, 9) # random number
                exponent_list = [sympy.Pow(x,r) % p  for x in packet_list[i][1]]
                c1 *= sympy.Pow(packet_list[i][0],r) % p
                c1 = c1 % p 
                exp_list.append(exponent_list)
                e.append(r)

            res = exp_list[0]
            for sublist in exp_list[1:]:
                res = [(a * b) % p for a,b in zip(res, sublist)]
            
            return c1, res, e
        
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
                        self.matrix.append(message['exponentes'])
                        self.packet_buffer.append(message['PACKET'])
                        print(f"Packets Comming from {self.s.getpeername()}") # Get the Address of the incomming packets (from where do they come)
                        Message.key = message["key"]
                        Message.p = message["p"]
                        Message.format = message['format']
                        # send linear combinations to other peers
                        #c1, c2, x = self.compute_linear_combinations(self.packet_buffer)
                        #lc_new = {"PACKET": (c1,c2), "exponentes": x, "key": self.elgamal.private_key, "p": self.elgamal.p, "L": len(self.packet_buffer), "format": Message.format}
                        #serialized_message = pickle.dumps(lc_new)
                        serialized_message = pickle.dumps(message)
                        serialized_message = bytes(f"{len(serialized_message):<{HEADERSIZE}}", 'utf-8')+serialized_message
                        #for p in p2p.connections:
                        #    p.send(serialized_message)
                        lenght = message['L']
                        ma = np.array(self.matrix)
                        rank = np.linalg.matrix_rank(ma)
                        q = (Message.p - 1) // 2
                        if rank % q == lenght:
                            # ready to decrypt the linear combinations
                            print("LC_list", self.packet_buffer)
                            Message.message = self.recalculate_result(self.packet_buffer, self.matrix, Message.p)
                            Message.message_ready = True
                            #self.packet_buffer = []
        except KeyboardInterrupt:
            self.send_disconnet_to_server()
            print("[*] Disconnect from the Network")
            sys.exit()
        except ConnectionResetError:
            #self.send_disconnet_to_server()
            print("[*] Connection Resetet by Server")
            # become the server
            #sys.exit()
        except OSError:
            print("OSERROR")
            pass
        except ValueError as e:
            #print(e)
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