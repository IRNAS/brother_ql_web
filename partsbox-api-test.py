# This is a simple API test script
import requests
import json
import yaml

with open('partsbox-config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

PARTSBOX_USER_URL = config["PARTSBOX_USER_URL"]
PARTSBOX_API_URL = config["PARTSBOX_API_URL"]
PARTSBOX_API_KEY = config["PARTSBOX_API_KEY"]

headers = {"Authorization": "APIKey "+PARTSBOX_API_KEY,"Content-Type": "application/json; charset=utf-8"}
part_id = "1xfmbcn948genbg9jt6wm6phgv"
data = {"part/id": part_id}

response = requests.post(PARTSBOX_API_URL+"/part/get", headers=headers, json=data)
data=response.json()["data"]

print("Status Code", response.status_code)
print(json.dumps(data, indent=4, sort_keys=True))

# Getting stock values per stock location
stock_status = {}
for item in data["part/stock"]:
    # if storage location already exist, calcualte the stock level
    if item["stock/storage-id"] in stock_status:
        stock_status[item["stock/storage-id"]]+=item["stock/quantity"]
    # else assing the value
    else:
        stock_status[item["stock/storage-id"]]=item["stock/quantity"]
    #remove locations with 0 stock
    if stock_status[item["stock/storage-id"]] == 0:
        del stock_status[item["stock/storage-id"]]

# Looking up human readable name
stock_status_named = {}

for key, value in stock_status.items():
    response = requests.post(PARTSBOX_API_URL+"/storage/get", headers=headers, json={"storage/id": key})
    data_storage = response.json()

    stock_status_named[data_storage["data"]["storage/name"]]=stock_status[key]

    print("Status Code", response.status_code)
    print(json.dumps(data_storage, indent=4, sort_keys=True))

print(stock_status_named)

partsbox_fields = {}
partsbox_fields["mpn"]=data["part/name"]
partsbox_fields["desc"]=data["part/linked-choices"]["description"]
partsbox_fields["location"]=str(stock_status_named).replace("{","").replace("}","").replace("'","")
partsbox_fields["url"]="https://partsbox.com/irnas/part/"+part_id

print(partsbox_fields)
