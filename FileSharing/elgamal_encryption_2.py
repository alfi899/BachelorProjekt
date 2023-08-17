import random

class Gamal:
    def __init__(self):
        self.a = random.randint(2, 10)
        self.q = random.randint(2, 1024)
        self.g = random.randint(2, self.q)
        self.key = self.gen_key(self.q)
        self.h = self.power(self.g, self.key, self.q)
        

    def gcd(self, a, b):
        if a < b:
            return self.gcd(b, a)
        elif a % b == 0:
            return b;
        else:
            return self.gcd(b, a % b)
        
    def gen_key(self, q):
        key =random.randint(2, q)
        while self.gcd(q, key) != 1:
            key = random.randint(2, q)
        return key

    def power(self, a, b, c):
        x = 1
        y = a
        while b > 0:
            if b % 2 != 0:
                x = (x * y) % c;
            y = (y * y) % c
            b = int(b / 2)
        return x % c
    
 
    def encryption(self, message):
        en_msg = []
        k = self.gen_key(self.q)
        s = self.power(self.h, k, self.q)
        p = self.power(self.g, k, self.q)

        for i in range(0, len(message)):
            en_msg.append(message[i])

        for i in range(0, len(en_msg)):
            en_msg[i] = s * en_msg[i]

        return p, en_msg

    def decrypt(self, c1, en_msg, key, q):
        dr_msg = []
        h = self.power(c1, key, q)
        for i in range(0, len(en_msg)):
            dr_msg.append(int(en_msg[i]/h))
        return dr_msg
