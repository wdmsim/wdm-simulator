import collections.abc

def update_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            # d[k] = update_dict(d.get(k, {}), v)
            d[k] = update_dict(d.get(k, dict()), v)
        else:
            d[k] = v
    return d
