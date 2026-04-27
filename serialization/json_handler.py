import json

def serialize(data):
    return json.dumps(data).encode("utf-8")

def deserialize(payload):
    return json.loads(payload.decode("utf-8"))
