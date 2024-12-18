import asyncio
import logging
import os
import threading
import time

from BlocksProcessor import BlocksProcessor
from TxAddrMappingUpdater import TxAddrMappingUpdater
from VirtualChainProcessor import VirtualChainProcessor
from dbsession import create_all
from helper import KeyValueStore
from cryptixd.CryptixdMultiClient import CryptixdMultiClient

logging.basicConfig(format="%(asctime)s::%(levelname)s::%(name)s::%(message)s",
                    level=logging.DEBUG if os.getenv("DEBUG", False) else logging.INFO,
                    handlers=[
                        logging.StreamHandler()
                    ]
                    )

# disable sqlalchemy notifications
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)

# get file logger
_logger = logging.getLogger(__name__)

# create tables in database
_logger.info('Creating DBs if not exist.')
create_all(drop=False)

cryptixd_hosts = []

for i in range(100):
    try:
        cryptixd_hosts.append(os.environ[f"CRYPTIXD_HOST_{i + 1}"].strip())
    except KeyError:
        break

if not cryptixd_hosts:
    raise Exception('Please set at least CRYPTIXD_HOST_1 environment variable.')

# create Cryptixd client
client = CryptixdMultiClient(cryptixd_hosts)


async def main():
    # initialize cryptixds
    await client.initialize_all()

    # wait for client to be synced
    while client.cryptixds[0].is_synced == False:
        _logger.info('Client not synced yet. Waiting...')
        time.sleep(60)

    # find last acceptedTx's block hash, when restarting this tool
    start_hash = KeyValueStore.get("vspc_last_start_hash")

    # if there is nothing in the db, just get the first block after genesis.
    if not start_hash:
        daginfo = await client.request("getBlockDagInfoRequest", {})
        start_hash = daginfo["getBlockDagInfoResponse"]["virtualParentHashes"][0]

    _logger.info(f"Start hash: {start_hash}")

    # create instances of blocksprocessor and virtualchainprocessor
    vcp = VirtualChainProcessor(client, start_hash)
    bp = BlocksProcessor(client, vcp)

    # start blocks processor working concurrent
    while True:
        try:
            await bp.loop(start_hash)
        except Exception:
            _logger.exception('Exception occured and script crashed..')
            raise


if __name__ == '__main__':
    tx_addr_mapping_updater = TxAddrMappingUpdater()


    # custom exception hook for thread
    def custom_hook(args):
        global tx_addr_mapping_updater
        # report the failure
        _logger.error(f'Thread failed: {args.exc_value}')
        thread = args[3]

        # check if TxAddrMappingUpdater
        if thread.name == 'TxAddrMappingUpdater':
            p = threading.Thread(target=tx_addr_mapping_updater.loop, daemon=True, name="TxAddrMappingUpdater")
            p.start()
            raise Exception("TxAddrMappingUpdater thread crashed.")


    # set the exception hook
    threading.excepthook = custom_hook

    # run TxAddrMappingUpdater
    # will be rerun
    _logger.info('Starting updater thread now.')
    threading.Thread(target=tx_addr_mapping_updater.loop, daemon=True, name="TxAddrMappingUpdater").start()
    _logger.info('Starting main thread now.')
    asyncio.run(main())