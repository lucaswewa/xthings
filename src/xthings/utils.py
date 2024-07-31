def pathjoin(pa, pb):
    pa = pa.rstrip("/")
    pb = pb.lstrip("/")

    return pa + "/" + pb
