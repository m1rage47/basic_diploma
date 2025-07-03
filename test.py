from api import requester

query_params = {"query": "Такси"}
data = requester(False, query_params)

if data:
    print("Done")

