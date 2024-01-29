import logging
import signalfx
import os
import time
import atexit
from lib import azurenfssnapshot

logger = logging.getLogger("nfs_snapshot")
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.setLevel(log_level)
sh = logging.StreamHandler()
sh.setLevel(log_level)
logger.addHandler(sh)

sfx_logger = logging.getLogger("signalfx.ingest")
sfx_logger.setLevel(log_level)
sfx_logger.addHandler(sh)

def run():
    logger.info("Starting job")
    sfx_token = os.environ.get("SFX_TOKEN")
    if not sfx_token:
        raise ValueError("Environment variable SFX_TOKEN not set")
    sfx_realm = os.environ.get("SFX_REALM", "eu0")
    logging.info(f"SignalFx realm: {sfx_realm}")

    extra_dimensions = {
        couple.split("=")[0]: couple.split("=")[1]
        for couple in os.environ.get("SFX_EXTRA_DIMENSIONS", "").split(",")
        if couple != ""
    }
    logging.info(f"Extra signalFx dimensions: {extra_dimensions}")
    sfx_clt = signalfx.SignalFx(
        api_endpoint=f"https://api.{sfx_realm}.signalfx.com",
        ingest_endpoint=f"https://ingest.{sfx_realm}.signalfx.com",
        stream_endpoint=f"https://stream.{sfx_realm}.signalfx.com",
    )

    logging.info("Init AzureNfsSnapshot class")
    az = azurenfssnapshot.AzureNfsSnapshot()

    with sfx_clt.ingest(sfx_token) as sfx:
        atexit.register(sfx.stop)

        logging.info("Start Parsing all Storage Account and shares for snapshots")
        for sa, value in az.filestorage_list.items():
            logging.info(f"Execute snapshot on {sa} - subscription: {value.subscription_id}")
            for share in az.list_shares(storage_account=sa):
                logging.info(f"Create snapshot on {sa} - {share.name}")
                #az.create_snapshot(storage_account=sa, share=share.name)
                # Create + send SFX Metrics
                sfx_metric = [
                    {
                        'metric': 'fame.azure.nfs.snapshot',
                        'value': 1,
                        'timestamp': round(time.time() * 1000),
                        'dimensions': {'storage_account_name': sa,
                                       'subscription_id': value.subscription_id,
                                       'env': value.tags['env'],
                                       'share_name': share.name
                                       }
                    }
                ]
                sfx.send(gauges=sfx_metric)

    logging.info("Job Done")

if __name__ == "__main__":
    run()
