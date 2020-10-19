import requests
import json
import logging
import pickle
from logging.handlers import TimedRotatingFileHandler

global parameters

api_key = ""  # Can be defined here or in the json file.
org_id = ""  # Can be defined here or in the json file.
path = "NetworkDownList.pickle"  # Name of serialized list file
url = "https://api.meraki.com/api/v1"  # base url
excludedIPs = ["8.8.8.8", "66.114.168.212", "104.129.198.179"]  # Specify a list of excluded IPs
networkDownList = []


def getUplinkStats(api_key, org_id):
    # "Utility function to return the uplink loss and latency for WAN1 on every MX in the org"
    try:
        get_url = "{0}/organizations/{1}/devices/uplinksLossAndLatency?uplink=wan1".format(
            url, org_id
        )
        headers = {
            "x-cisco-meraki-api-key": format(str(api_key)),
            "Content-Type": "application/json",
        }
        response = requests.get(get_url, headers=headers)
        response_json = json.loads(response.text)

        if response.status_code == 200:
            return response_json

        else:
            logging.error(
                "Error encountered when making API call:" + str(response.status_code)
            )
            exit(0)
    except Exception as e:
        logging.error("Error encountered when making API call: " + str(e))
        exit(0)


def getNetwork(api_key, network):
    # "Utility function to return single network information"
    try:
        get_url = "{0}/networks/{1}/".format(url, network)
        headers = {
            "x-cisco-meraki-api-key": format(str(api_key)),
            "Content-Type": "application/json",
        }
        response = requests.get(get_url, headers=headers)
        response = json.loads(response.text)
        return response
    except Exception as e:
        logging.error("Error encountered when making API call: " + str(e))
        exit(0)


def importJson(filename):
    # "Imports JSON parameter file"
    try:
        with open(filename, "r") as jsonFile:
            jsonObj = json.load(jsonFile)
        return jsonObj
    except Exception as e:
        logging.error(
            "Error encountered when loading JSON configuration file: " + str(e)
        )
        exit(0)


def updateNetworkTags(api_key, network, payload):
    # "Utility function to update network configuration"

    try:
        get_url = "{0}/networks/{1}".format(url, network)
        headers = {
            "x-cisco-meraki-api-key": format(str(api_key)),
            "Content-Type": "application/json",
        }
        response = requests.put(get_url, headers=headers, data=json.dumps(payload))
        return response
    except Exception as e:
        logging.error("Error encountered when making API call: " + str(e))
        exit(0)


def readPickle(path, default):
    # "Function attempts to open an existing file with list. Otherwise will return an empty list."

    try:
        default = pickle.load(open(path, "rb"))
        return default
    except (OSError, IOError) as e:
        logging.info("No existing Network Down List: " + str(e))
        return default


def writePickle(path, default):
    # "Writes list to existing file"

    try:
        pickle.dump(default, open(path, "wb"))
    except (OSError, IOError) as e:
        logging.error("Could not write list to file: " + str(e))


def VPNFailback(network, loss):
    # "Swaps tags when the primary VPN is healthy"

    if loss is False and network["networkId"] in networkDownList:
        network_info = getNetwork(api_key, network["networkId"])
        tags = network_info["tags"]
        print("Primary VPN healthy again ... Swapping back")
        print("Network to Swap Back: ", network_info["name"], " // Network ID: ", network["networkId"], " // ZScaler IP: ", network["ip"], " // Loss:", loss, " // Initial Tags: ", tags)

        for i, tag in enumerate(tags):
            if "_ZS_P_DOWN" in tag:
                tag = tag.replace("_DOWN", "_UP")
                tags[i] = tag
            elif "_ZS_B_UP" in tag:
                tag = tag.replace("_UP", "_DOWN")
                tags[i] = tag

        payload = {"tags": tags}
        print("New Tags: ", payload)
        updateNetworkTags(api_key, network["networkId"], payload)
        networkDownList.remove(network["networkId"])
        logging.info(
            "FAILBACK - Primary VPN healthy again: {0} IP:{1}.".format(
                network_info["name"], network["ip"]
            )
        )
    return


def VPNFailover(tags, network, network_name, timeseries):
    # "Iterates through list of tags, updating the values without overiding"
    for i, tag in enumerate(tags):
        #print(tag)
        if "_ZS_P_DOWN" in tag:
            print("Network Already in Backup Mode")
            return
        elif "_ZS_P_UP" in tag:
            tag = tag.replace("_UP", "_DOWN")
            tags[i] = tag
        elif "_ZS_B_DOWN" in tag:
            tag = tag.replace("_DOWN", "_UP")
            tags[i] = tag
    payload = {"tags": tags}
    print("New Tags: ", payload)
    updateNetworkTags(api_key, network["networkId"], payload)
    networkDownList.append(network["networkId"])
    logging.info(
        "FAILOVER - {0} IP:{1} Loss: {2} Latency{3}.".format(
            network_name,
            network["ip"],
            timeseries["lossPercent"],
            timeseries["latencyMs"],
        )
    )
    return


def networkHealthCheck(network, loss):
    # "Iterates through timeseries list to find cases where losspercent is >=30% or latency is >=100ms"

    for i in network["timeSeries"]:
        if i["lossPercent"] >= 30 or i["latencyMs"] >= 100:
            loss = True
            network_info = getNetwork(api_key, network["networkId"])
            network_name = network_info["name"]
            tags = network_info["tags"]
            print("Network to Failover: ", network_name, " // Network ID: ", network["networkId"], " // ZScaler IP: ", network["ip"], " // Loss:", loss, " // Initial Tags: ", tags)
            VPNFailover(tags, network, network_name, i)
            break
    return loss


def sortNetworkMain(org):  # first function to be called
    # "Iterates through list of networks in the organization (main function)"

    for network in org:
        if network["ip"] not in excludedIPs:
            loss = False
            loss = networkHealthCheck(network, loss)
            VPNFailback(network, loss)
    return


if __name__ == "__main__":

    # Defines Log File
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logHandler = TimedRotatingFileHandler(
        "meraki_zscaler_vpn_health.log", when="D", interval=30, backupCount=6
    )
    logHandler.setLevel(logging.INFO)
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)

    # Collects parameters from Json file
    parameters = importJson("meraki_parameters.json")
    api_key = parameters["meraki"]["api_key"]
    org_id = parameters["meraki"]["org_id"]

    # Reads serialized file for latest version of networkDownList
    networkDownList = readPickle(path, networkDownList)
    # Retrieves uplink loss & latency information for organization
    org = getUplinkStats(api_key, org_id)
    # print(org)
    # Iterates through networks to determine if VPN needs to be swapped
    sortNetworkMain(org)
    # Writes to serialized file with latest version of networkDownList
    print(networkDownList)
    writePickle(path, networkDownList)
