import os
import sys
from multiprocessing import Manager
from src.utils.logger import CLOG
from playsound import playsound
import time

def runSOUND(guiState, soundState, silence):
    sound = Sound(guiState, soundState, silence)
    sound.run()
    sound.shutdown()

def soundStateInit(soundState):
    soundState['Lana'] = False

class Sound():
    def __init__(self, guiState, soundState, silence=False, parent=None):
        # COMMUNICATION BETWEEN THREADS
        self.guiState = guiState
        self.soundState = soundState
        self.cl = CLOG(processName="SOUND", timed=True, silence=silence)
        
    def run(self):
        self.cl.log('Starting up')
        self.soundCheckLoop()
    
    def soundCheckLoop(self):
        while (True):
            if self.soundState['Lana']:
                self.soundState['Lana'] = False
                playsound('Lana.mp3')
            
            time.sleep(0.2)
            
            if self.guiState['shutdown']:
                break
  
    def shutdown(self):
        self.cl.log('Graceful shutdown')
