from azure_nfs_snapshot import create_snapshot, purge_snapshot, snapshots_metric
import azure.functions as func
import logging
import os
import requests

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=logging.getLevelName(log_level), format='%(asctime)s %(levelname)-8s %(message)s')
sh = logging.StreamHandler()

# Remove HTTP to SA from Azure Function
if log_level != "DEBUG":
    logger_az_func = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
    logger_az_func.setLevel(logging.WARNING)

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 2 * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def NfsSnapshot(myTimer: func.TimerRequest) -> None:

    logging.info(f"Outgoing Ip: {requests.get('https://ip.clara.net').text}")
    if myTimer.past_due:
        logging.info('The timer is past due!')
    logging.info('NfsSnapshot - Running - create_snapshot.run()')
    create_snapshot.run()
    logging.info('NfsSnapshot - Terminated - create_snapshot.run()')
    logging.info('NfsSnapshot - Running - purge_snapshot.run()')
    purge_snapshot.run()
    logging.info('NfsSnapshot - Terminated - purge_snapshot.run()')
    logging.info('NfsSnapshot - Running - snapshots_metric.run()')
    snapshots_metric.run()
    logging.info('NfsSnapshot - Terminated - snapshots_metric.run()')

