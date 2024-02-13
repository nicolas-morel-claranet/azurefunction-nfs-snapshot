import logging
import os
from operator import attrgetter
from lib import azurenfssnapshot

logger = logging.getLogger("nfs_snapshot_purge")
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.setLevel(log_level)
sh = logging.StreamHandler()
sh.setLevel(log_level)
logger.addHandler(sh)


def run():
    logger.info("Starting purge_snapshot")
    snapshot_history = os.environ.get("SNAPSHOT_HISTORY", 7)

    logging.info("Init AzureNfsSnapshot class")
    az = azurenfssnapshot.AzureNfsSnapshot()
    logging.info(
        f"Nb of Storage Account detected: {len(az.filestorage_list.items())}")
    for sa, value in az.filestorage_list.items():
        logging.info(
            f"Execute pruge snapshot on {sa} - subscription: {value.subscription_id}"
        )
        snapshots_list = sorted(
            az.list_snapshot(storage_account=sa), key=attrgetter("snapshot")
        )
        snapshot_diff = len(snapshots_list) - snapshot_history
        logger.info(
            f"Storage Acccount : {sa} - Nb Snapshot : {len(snapshots_list)}"
        )
        if len(snapshots_list) > snapshot_history:
            for snapshot in snapshots_list[:snapshot_diff]:
                logger.info(f"Delete {snapshot.snapshot} on {sa} - {snapshot.name}")
                az.delete_snapshot(storage_account=sa, share=snapshot.name, snapshot=snapshot.snapshot)

    logging.info("purge_snapshot - Job Done")


if __name__ == "__main__":
    run()
