def pathjoin(pa, pb):
    while pa.endswith("/"):
        pa = pa[:-1]

    while pb.startswith("/"):
        pb = pb[1:]

    return pa + "/" + pb
