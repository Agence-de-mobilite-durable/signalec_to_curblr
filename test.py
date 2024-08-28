""" Main file to test the inventory preprocessing
"""
import logging
from cygne.preprocessing.inventory import main

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S",
    filename='tests/problemes_detecte_inventaire.log',
    filemode='w+'
)
logger = logging.getLogger('cygne-inventory-test')

if __name__ == "__main__":
    logger.info('Start testing')
    main()
