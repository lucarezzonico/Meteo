import multiprocessing as mp
from gui import runGUI, guiStateInit
from sound import runSOUND, soundStateInit

SILENCE = False

def startThreads(manager, silence):
    guiState = manager.dict()
    guiStateInit(guiState)
    
    soundState = manager.dict()
    soundStateInit(soundState)
    
    pGUI = mp.Process(target=runGUI, args=(guiState, soundState, silence))
    pSOUND = mp.Process(target=runSOUND, args=(guiState, soundState, silence))
    
    pGUI.start()
    pSOUND.start()
    
    pGUI.join()
    pSOUND.join()


if __name__ == "__main__":
    mp.freeze_support()
    mp.set_start_method('spawn')
    with mp.Manager() as manager:
        startThreads(manager=manager, silence=SILENCE)