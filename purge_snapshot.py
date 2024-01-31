import logging
import signalfx
import os
import time
import atexit
from operator import itemgetter, attrgetter
from lib import azurenfssnapshot
from datetime import datetime

logger = logging.getLogger("nfs_snapshot_purge")
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
    snapshot_history = os.environ.get("SNAPSHOT_HISTORY", 2)
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

    for sa, value in az.filestorage_list.items():
        logging.info(
            f"Execute pruge snapshot on {sa} - subscription: {value.subscription_id}")
        snapshots_list = sorted(az.list_snapshot(storage_account=sa),
                                key=attrgetter('snapshot'))
        snapshot_diff = len(snapshots_list) - snapshot_history
        print(
            f"{sa} - Nb Snapshot : {len(snapshots_list)} - Diff - {str(snapshot_diff)}")
        if len(snapshots_list) > snapshot_history:
            for snapshot in snapshots_list[:snapshot_diff]:
                print(f"Delete {snapshot.snapshot} on {sa} - {snapshot.name}")
                # az.delete_snapshot(storage_account=sa, share=snapshot.name, snapshot=snapshot.snapshot)

    logging.info("Begin collect metrics for splunk")
    with sfx_clt.ingest(sfx_token) as sfx:
        atexit.register(sfx.stop)
        for



    logging.info("Job Done")

if __name__ == "__main__":
    run()
