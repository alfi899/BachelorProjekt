import json
import random
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
import sympy

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
        #self.my_public_key = self.elgamal.h
        self.file_format = ""
        self.new_filename = ""
        self.packet_number = ""
        self.total_packets = ""

        self.flag = True

        self.prime_number_q = 911
        self.prime_number_p = 2*self.prime_number_q + 1

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        
        def send_button_function():
            self.home_frame.grid_forget()
            self.send_frame.grid(row=0, column=1, sticky="nsew")
            print("Go to send Frame")
            

        def receive_button_function():
            if Message.message_ready == True:
                self.home_frame.grid_forget()
                self.receive_frame.grid(row=0, column=1, sticky="nsew")
                print("Go to receive Frame")
                receive_file_button = customtkinter.CTkButton(self.receive_frame, text="Get File", command=receive_message)
                receive_file_button.grid(row=3, column=1, padx=180, pady=40)
            else:
                print("[*] Not enough linear combinations to recover the file")
            #while True:
            #    show_received_message = customtkinter.CTkLabel(self.receive_frame, text=len(Message.message), width=100, height=4)
            #    show_received_message.grid(row=4, column=1, padx=200, pady=50)

            #    if len(Message.message) != 0:
            #        receive_file_button = customtkinter.CTkButton(self.receive_frame, text="Get File", command=receive_message)
            #        receive_file_button.grid(row=3, column=1, padx=180, pady=40)

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
                    padding = bytes([1] * (target_size - len(packet)))
                    padded_packet = packet + padding
                    padded_packets.append(padded_packet)
                else:
                    padded_packets.append(packet)
            return padded_packets
        
        def unpad_packets(padded_packets):
            unpadded_packets = []
            for packet in padded_packets:
                # Remove Padding. Remove the Nullbytes at the end
                unpadded_packet = packet.rstrip(b'\x01')
                unpadded_packets.append(unpadded_packet)
            return unpadded_packets
        
        def join_packets(packets):
            return b''.join(packets)


        def compute_linear_combinations(packet_list):
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
            

        def send_message():
            """send the packets to the connected peers.
                1. split the file in equally sized packets
                2. Encrypt every single packet with elgamal encryption
                3. create linear combinations of the enctypted values
                    (c1,c2)^a * (c1,c2)^b * c1,c2)^c ...
                4. Save the coefficients (a,b,c) in a matrix and send it with the packets
            """
            packet_size = 64 #128 #256 # target packet size
            packets = split_file_into_packets(self.filename, packet_size)
            padded_packets = pad_packets(packets, packet_size)
            
            """ Encrypt every package using elgamal """
            encrypted_packets = []
            for i in range(0, len(padded_packets)):
                encrypted_packet = self.elgamal.encryption(padded_packets[i]) #(c1, 2)
                encrypted_packets.append(encrypted_packet)
            #print(encrypted_packets)
            lc = []
            m = []
            """ Generate the linear combinations """
            #while True:
            for i in range(0, len(encrypted_packets)):
                c1,c2,x = compute_linear_combinations(encrypted_packets)
                lc.append((c1,c2))
                m.append(x)

                #print(f"key: {self.elgamal.public_key}, q: {self.elgamal.q}")
                """ Continously send linear combinations out
                    (But for testing we only send each lc once)"""
                send_formated({"PACKET": (c1,c2), "exponentes": x, "key": self.elgamal.private_key, "p": self.elgamal.p, "L": len(encrypted_packets), "format": self.file_format}, i, len(encrypted_packets))
                time.sleep(0.1)


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
                        #print(f"[*] Sended packet successfully {number+1} / {total}")
                    except:
                        print(f"[*] Failed to send message")

        def receive_message():
            """ Receive the file.
                1. Get all informations from every single packet
                2. use inverse matrix multiplication to get back to the decoded packet
                3. Use elgamal decryption to decrypt the packet back to it's original
                4. Write the packets to a file and safe it 
            """
            #print(Message.message)
            s = list(itertools.chain.from_iterable(Message.message))
            s = [int(x) for x in s]
            res = []
            file = []
            for i in range(0, len(s)):
                res.append(int.to_bytes(s[i], 1, 'big'))
            st = b''.join(res)
            file.append(st)
    
            unpadded_packets = unpad_packets(file)
            reconstructed_data = join_packets(unpadded_packets)
            #print(reconstructed_data)
            new_file = "Received_file"+Message.format
            
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


        
    def on_closing(self):
        print("Destroy GUI")
        p2p.stop = True
        self.flag = False
        self.destroy()
        #quit()


def foreground():
    global app
    app = App2()
    app.mainloop()

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
        print("Exit")
        sys.exit("EEEXXIIIT")

if __name__=="__main__":
    b = threading.Thread(name="background", target=background)
    f = threading.Thread(name="foreground", target=foreground)
    #b.daemon = True
    f.start()
    b.start()

    