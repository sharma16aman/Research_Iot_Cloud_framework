import json

def dumps(obj):
    return json.dumps(obj).encode("utf-8")

def loads(b):
    return json.loads(b.decode("utf-8"))
