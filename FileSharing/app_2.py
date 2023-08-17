import json
import os
import pickle
import sys
import threading
import time
from PIL import Image
import customtkinter
from tkinter import filedialog as fd
from CTkTable import *
import numpy as np
import itertools
import socket

from helper_2 import ServerRunning
from server_2 import StartGenesisNode
from helper_2 import p2p, Message, NumpyArrayEncoder
from elgamal_encryption_2 import Gamal
from peer_2 import Peer


class App2(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.title("File Transfer")
        self.geometry("600x400")
        self.resizable(0,0)

        self.home_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.home_frame.grid(row=0, column=1, sticky="nsew")

        self.send_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.receive_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
         # load images
        image_path = os.path.join(os.getcwd(), "images")
        self.home_image = customtkinter.CTkImage(dark_image=Image.open(os.path.join(image_path, "home_light.png")), size=(20,20,))

        self.filename = ""
        self.elgamal = Gamal()
        self.file_format = ""
        self.new_filename = ""
        self.packet_number = ""
        self.total_packets = ""
        
        def send_button_function():
            self.home_frame.grid_forget()
            self.send_frame.grid(row=0, column=1, sticky="nsew")
            print("Go to send Frame")
            

        def receive_button_function():
            self.home_frame.grid_forget()
            self.receive_frame.grid(row=0, column=1, sticky="nsew")
            print("Go to receive Frame")
            while True:
                show_received_message = customtkinter.CTkLabel(self.receive_frame, text=len(Message.message), width=100, height=4)
                show_received_message.grid(row=4, column=1, padx=200, pady=50)

                if len(Message.message) != 0:
                    receive_file_button = customtkinter.CTkButton(self.receive_frame, text="Get File", command=receive_message)
                    receive_file_button.grid(row=3, column=1, padx=180, pady=40)

        def back_to_home_from_S():
            self.send_frame.grid_forget()
            self.home_frame.grid(row=0, column=1, sticky="nsew")

        def back_to_home_from_R():
            self.receive_frame.grid_forget()
            self.home_frame.grid(row=0, column=1, sticky="nsew")
        
        def open_file():
            filetypes = (('text files', '*.txt'), ('All files', '*.*'))
            # select one or more files
            self.filename = fd.askopenfilename(filetypes=filetypes)
            
            #change label content
            label_file_explorer.destroy()
            #label_file_explorer.configure(text="File Opened: "+filename)

            if self.filename:
                display_file(self.filename)

        def display_file(filepath):
            filename = os.path.basename(filepath)
            size = os.path.getsize(filepath)
            file_format = os.path.splitext(filepath)[1]
            self.file_format = file_format
            self.new_filename = filename

            data = [["Name", "Size (bytes)", "Format"],
                    [filename, size, file_format]]

            table = CTkTable(master=self.send_frame, row=len(data), column=3, values=data)
            table.grid(row=1, column=1, padx=10, pady=30)

            send_button = customtkinter.CTkButton(self.send_frame, text="Send", command=send_file_to_all_peers)
            send_button.grid(row=2, column=1, padx=10, pady=10)


        def split_file_into_packets(file_path, packet_size):
            packets = []
    
            with open(file_path, 'rb') as file:
                while True:
                    packet = file.read(packet_size)
                    if not packet:
                        break
                    packets.append(packet)
    
            return packets
        
        def pad_packets(packets, target_size):
            padded_packets = []
            for packet in packets:
                if len(packet) < target_size:
                    padding = bytes([0] * (target_size - len(packet)))
                    padded_packet = packet + padding
                    padded_packets.append(padded_packet)
                else:
                    padded_packets.append(packet)
            return padded_packets
        
        def unpad_packets(padded_packets):
            unpadded_packets = []
            for packet in padded_packets:
                # Remove Padding. Remove the Nullbytes at the end
                unpadded_packet = packet.rstrip(b'\x00')
                unpadded_packets.append(unpadded_packet)
            return unpadded_packets
        
        def join_packets(packets):
            return b''.join(packets)


        def random_matrix_over_GF(n, rows, cols):
            random_matrix = np.random.randint(0, n, size=(rows, cols))

            gf_matrix = random_matrix % n

            return gf_matrix

        def send_message():
            """send the packets to the connected peers.
                1. split the file in equally sized packets
                2. Encrypt every single packet with elgamal encryption
                3. generate a random matrix
                4. Encode every packet and send it over the network
            """
            packet_size = 128 #256 # target packet size
            packets = split_file_into_packets(self.filename, packet_size)
            padded_packets = pad_packets(packets, packet_size)
            print(f"len(packets): {len(padded_packets)}")
           
            
            # encrypt the packets with elgamal
            encrypted_packets_vector = []
            c1_vector = []
            for i in range(0, len(padded_packets)):
                c1, encrypted_packet = self.elgamal.encryption(padded_packets[i])
                encrypted_packets_vector.append(encrypted_packet)
                c1_vector.append(c1)
                       

            ## generate random matrix over the field GF(5) (maybe change to bigger one later)
            gf = 5
            size = packet_size
            matrix = random_matrix_over_GF(gf, size, size)
            
            ### Encode the encrypted packets
            count = 0

            self.total_packets = len(encrypted_packets_vector)
            
            for i in range(0, len(encrypted_packets_vector)):
                encoded_packet = np.dot(matrix, encrypted_packets_vector[i])
                self.packet_number = i
                # send the packet for now to all peer's, but later maybe only to a random selected peers
                # and send the c1 value for decryption later
                # for now send the matrix with every packet for the decoding process
                send_formated({"PACKET": i,"GESAMT": self.total_packets ,"FORMAT": self.file_format, 
                               "matrix": matrix, "encoded_packet": encoded_packet, "c1": c1_vector[i], 
                               "key": self.elgamal.key, "q": self.elgamal.q}, i, len(encrypted_packets_vector))
                #send_formated({"PACKET": i, "matrix": "matrix", "encoded_packet": "encoded_packet", "c1": "c1_vector[i]", "key": "self.elgamal.key", "q": "self.elgamal.q"})
                time.sleep(1)
                count += 1
            
            if count == len(encrypted_packets_vector):
                print("[*] Successfully send all packets")




        def send_formated(message, number, total):
            """ prepare the message befor sending it. Use pickle
                for better handling and use HEADERSIZE to know the length of the packet
            """
            serialized_message = pickle.dumps(message)
            HEADERSIZE = 10
            serialized_message = bytes(f"{len(serialized_message):<{HEADERSIZE}}", 'utf-8')+serialized_message
            if len(p2p.connections) != 0:
                for p in p2p.connections:
                    try:
                        p.send(serialized_message)
                        print(f"[*] Sended packet successfully {number+1} / {total}")
                    except:
                        print(f"[*] Failed to send message")

        def receive_message():
            """ Receive the file.
                1. Get all informations from every single packet
                2. use inverse matrix multiplication to get back to the decoded packet
                3. Use elgamal decryption to decrypt the packet back to it's original
                4. Write the packets to a file and safe it 
            """
            print(f"Message length: {len(Message.message)}")
            #if len(Message.message) != 0:
            #    show_received_message = customtkinter.CTkLabel(self.receive_frame, text="Message Received", width=100, height=4)
            #    show_received_message.grid(row=4, column=1, padx=200, pady=50)
            #else:
            #    show_received_message = customtkinter.CTkLabel(self.receive_frame, text="No Messages", width=100, height=4)
            #    show_received_message.grid(row=4, column=1, padx=200, pady=50)

            decoded_packets_vector = []
            decrypted_packets_vector = []
            # Do this for every package that is received
            for i in range(0, len(Message.message)):
                message = Message.message[i]
                packet_number = message["PACKET"]
                file_format = message["FORMAT"]
                matrix = np.array(message["matrix"])
                packet = message["encoded_packet"]
                c1 = message["c1"]
                key = message["key"]
                q = message["q"]
                print(f"Packet: {packet_number}")
                print(f"matrix: {matrix}")
                print(f"packet: {packet}")
                print(f"c1: {c1}")
                print(f"key: {key}")
                print(f"q: {q}")
                
                ## decode packet with inverse matrix multiplication
                inverse_matrix = np.linalg.inv(matrix)
                decoded_packet_tmp = np.dot(inverse_matrix, packet)
                res = np.round(decoded_packet_tmp)
                decoded_packet = res.astype(int).tolist()
                decoded_packets_vector.append(decoded_packet)
                
                print(f"[*] Decoded Packet successfull with inverseve matrix multiplication")
                
                dec_packet = self.elgamal.decrypt(c1, decoded_packet, key, q)
                decrypted_packets_vector.append(dec_packet)
                
            s = list(itertools.chain.from_iterable(decrypted_packets_vector))
            res = []
            for i in range(0, len(s)):
                res.append(int.to_bytes(s[i], 1, 'big'))
            concatenated_string = b''.join(res)
            nl = []
            nl.append(concatenated_string)

            unpadded_packets = unpad_packets(nl)
            reconstructed_data = join_packets(unpadded_packets)

            new_file = "Received_file"+file_format
            
            with open(new_file, "wb") as file:
                file.write(reconstructed_data)
            
            print("[*] Data has successfull been written to the file")

           


        def send_file_to_all_peers():
            send_message()
            



        # Home frame
        self.button = customtkinter.CTkButton(self.home_frame, text="Send", command=send_button_function)
        self.button.grid(row=0, column=0, padx=80, pady=200)
        self.button2 = customtkinter.CTkButton(self.home_frame, text="Receive", command=receive_button_function)
        self.button2.grid(row=0, column=1, padx=80, pady=200)

        self.ip = socket.gethostname()

        # Send Frame
        self.back_button_send = customtkinter.CTkButton(self.send_frame, text="",image=self.home_image, command=back_to_home_from_S,
                                                        fg_color="transparent", width=20, font=customtkinter.CTkFont(size=30))
        self.back_button_send.grid(row=0, column=0)
        label_file_explorer = customtkinter.CTkLabel(self.send_frame, text="No file selected", width=100, height=4)
        label_file_explorer.grid(row=1, column=1, padx=180, pady=40)
        self.open_file_button = customtkinter.CTkButton(self.send_frame, text="Open File", command=open_file)
        self.open_file_button.grid(row=3, column=1, padx=180, pady=40)

        # Receive Frame
        self.back_button_receive = customtkinter.CTkButton(self.receive_frame, text="",image=self.home_image, command=back_to_home_from_R,
                                                        fg_color="transparent", width=20, font=customtkinter.CTkFont(size=30))
        self.back_button_receive.grid(row=0, column=0)
        #self.receive_file_button = customtkinter.CTkButton(self.receive_frame, text="Get File", command=receive_message)
        #self.receive_file_button.grid(row=3, column=1, padx=180, pady=40)

        # Show IP and Connections
        while True:
            self.ip_label = customtkinter.CTkLabel(self.home_frame, text=self.ip, width=100, height=4)
            self.ip_label.grid(row=3, column=1, padx=10, pady=10)

            self.connections_number = len(p2p.connections)



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

def foreground():
    app = App2()
    app.mainloop()

if __name__=="__main__":
    b = threading.Thread(name="background", target=background)
    f = threading.Thread(name="foreground", target=foreground)
    b.start()
    f.start()