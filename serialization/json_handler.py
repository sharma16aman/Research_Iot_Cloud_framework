try:
    import cbor2
except Exception as e:
    cbor2 = None

def dumps(obj):
    if cbor2 is None:
        raise RuntimeError("cbor2 not installed")
    return cbor2.dumps(obj)

def loads(b):
    if cbor2 is None:
        raise RuntimeError("cbor2 not installed")
    return cbor2.loads(b)
