import os
import logging
from logging.handlers import RotatingFileHandler
from modules.Config import config

LogLevel = logging.INFO

try:
    # Set up log handler
    LogFormatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(line:%(lineno)d) %(message)s')
    ConsoleFormatter = logging.Formatter('%(asctime)s - %(message)s')
    LogPath = 'logs'
    LogFile = f'{LogPath}/debug.log'
    os.makedirs(LogPath, exist_ok=True)  # Create logs directory if not exist

    # Set up log file rotation handler
    LogHandler = RotatingFileHandler(LogFile, maxBytes=20 * 1024 * 1024, backupCount=5)
    LogHandler.setFormatter(LogFormatter)
    LogHandler.setLevel(logging.INFO)

    # Set up console log stream handler
    ConsoleHandler = logging.StreamHandler()
    ConsoleHandler.setFormatter(ConsoleFormatter)
    ConsoleHandler.setLevel(LogLevel)

    # Create logger and attach handlers
    log = logging.getLogger('root')
    log.setLevel(logging.INFO)
    log.addHandler(LogHandler)
    log.addHandler(ConsoleHandler)

    match config['bot_mode']:
        case 'spin':
            from modules.gen3.rse.General import ModeSpin
            ModeSpin()

except Exception as e:
    print(str(e))
    input('Press enter to continue...')
    os._exit(1)