import socket
import threading
import pickle
import random
import numpy as np
import sys
import time
import sympy
import itertools


from helper_2 import ServerRunning, p2p, Message
from elgamal_encryption_2 import Gamal

HEADERSIZE = 10

class StartGenesisNode:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('127.0.0.1', 5000))
        self.s.listen(3)

        # Server IP drinnen, sodass spätere peers sich auch mit dem server Node verbinden können
        self.peers = [] # ('127.0.0.1', 5000)
        self.connections = []

        self.matrix = []
        self.packet_buffer = []

        print("[*] Server Node Started")
        print("[*] Waiting for connections...")

        ServerRunning.isRunning = True
        
        self.elgamal = Gamal()


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
            print(self.peers)
            #p2p.peer_list.append(a)

    
    def recalculate_result(self, lc, matrix, p):
        dec = [self.elgamal.decryption(lc[i][0], lc[i][1], Message.key) for i in range(len(lc))]
        
        #print("DEC: ", dec)
        m = sympy.Matrix(matrix)
        q = (p-1) // 2
        matrix_inverse = m.inv_mod(q)
        #print("INVERSE Matrix: ", matrix_inverse)

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
        public_key = "public_key"
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
                        #print(message)
                        self.matrix.append(message['exponentes'])
                        self.packet_buffer.append(message['PACKET'])
                        print(f"[*] Packets comming from {c.getpeername()}")
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
                            #print("LC_list", self.packet_buffer)
                            Message.message = self.recalculate_result(self.packet_buffer, self.matrix, Message.p)
                            Message.message_ready = True
                            print("[*] File Decrypted")
                    elif public_key in message:
                        print(f"[*] Received public_key from {a}")
                        print(f"public_key: {message}")
                    elif disconnect in message:
                        self.disconnect_peer(c, a)
                        break
        except ConnectionResetError:
            self.disconnect(c, a)
        except OSError:
            self.disconnect_peer(c, a)
        except ValueError:
            pass
        except KeyboardInterrupt:
            print("[*] Disconnect from the Network")
            sys.exit()
                    
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