from json import JSONEncoder
import numpy as np


class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)


class ServerRunning:
    isRunning = False

class p2p:
    peer_list = ['127.0.0.1']
    peers = []
    connections = []
    running = True


class Message:
    message = []