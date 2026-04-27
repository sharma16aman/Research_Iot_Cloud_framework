import cbor2

def serialize(data):
    return cbor2.dumps(data)

def deserialize(payload):
    return cbor2.loads(payload)
