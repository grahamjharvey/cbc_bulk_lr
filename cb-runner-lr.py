#!/usr/bin/env python3

import csv
import json
import sys

from cbapi import CbDefenseAPI
from cbapi.example_helpers import build_cli_parser, get_cb_defense_object, get_cb_psc_object
from cbapi.psc import Device
from concurrent.futures import as_completed
from datetime import datetime, timezone, timedelta


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def check_last_contact(last_contact_time):
    last_contact_time = datetime.strptime(last_contact_time, "%Y-%m-%dT%H:%M:%S.%f%z")
    utcnow = datetime.now(timezone.utc).isoformat()
    utcnow = datetime.strptime(utcnow, "%Y-%m-%dT%H:%M:%S.%f%z")
    time_delta = utcnow - last_contact_time
    total_seconds = time_delta.total_seconds()
    minutes = divmod(total_seconds, 60)[0]

    return minutes

def run_actions(actions, cb_def, cb_psc, args):

    job = __import__(args.job)

    completed_sensors = []
    offline_sensors = []
    futures = {}

    
    with open(actions, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        print(f"{bcolors.HEADER}CHECKING DEVICE STATUS{bcolors.ENDC}")
        line_count = 0
        for row in csv_reader:
            device_id = row["DeviceId"]
            device_name = row["DeviceName"]
            action = row["Command"] + ";" + row["Resource"]
            dev_info = cb_psc.select(Device, device_id)
            minutes_since_last_contact = check_last_contact(dev_info.last_contact_time)

            if minutes_since_last_contact > 20:
                print(f"{bcolors.WARNING}DEVICE OFFLINE{bcolors.ENDC}: {device_id} {device_name} has not checked in for more than 20 minutes")
                #print("{bcolors.WARN}DEVICE OFFLINE{bcolors.ENDC}: {0} {1}. Has not checked in for more than 20 minutes".format(device_id, device_name))
            else:
                jobobject = job.getjob(action)
                print(f"{bcolors.OKBLUE}DEVICE ONLINE{bcolors.ENDC} : {device_id} {device_name} processing {action}.")
                #print("{0} {1} Processing command <{2}> for <{3}>...".format(row["DeviceId"],row["DeviceName"],row["Command"],row["Resource"]))

                f = cb_def.live_response.submit_job(jobobject.run, device_id)
                futures[f] = device_id
    
    print(f"{bcolors.HEADER}CHECKING JOB STATUS{bcolors.ENDC}")

    for f in as_completed(futures.keys(), timeout=600):
        if f.exception() is None:
            print(f"{bcolors.OKGREEN}SUCCESS{bcolors.ENDC} : {futures[f]} job completed ({f.result()})")
            completed_sensors.append(futures[f])
            #f.bypass(False)
        else:
            print(f"{bcolors.FAIL}DEVICE ERROR{bcolors.ENDC}  : {futures[f]} had the following error: {bcolors.FAIL}{f.exception()}{bcolors.ENDC}")


def main():

    parser = build_cli_parser("CB Runner")
    subparsers = parser.add_subparsers(help="Sensor commands", dest="command_name")

    parser.add_argument("-J", "--job",
                        action="store", required=False, default="job",
                        help="Name of the job to run.")
    parser.add_argument("-LR", "--lrprofile",
                        action="store", required=False,
                        help="Live Response profile name configured in your \
                              credentials.psc file.")
    parser.add_argument("-A", "--actions", required=True,
                        help="CSV file with a list of actions to run in the format \
                              of 'DeviceId, DeviceName, Command, Resource'")
    args = parser.parse_args()

    cb_psc = get_cb_psc_object(args)
    cb_def = CbDefenseAPI(profile=args.lrprofile)

    run_actions(args.actions, cb_def, cb_psc, args)


if __name__ == "__main__":
    sys.exit(main())
