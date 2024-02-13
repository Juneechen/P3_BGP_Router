def parse_ip(ip):
    ''' 
    ip in dotted decimal notation to integer
    '''
    return sum(int(x) << (24 - i * 8) for i, x in enumerate(ip.split('.')))

def custom_sort(entry):
    ''' 
    entry tuple (network, route, mask_int), 
    route has key {"network",
                "netmask",
                "localpref",
                "ASPath",
                "origin",
                "selfOrigin", 
                "nexthop"}
    apply multi-level sort by localpref, selfOrigin, len(ASPath), origin, and longest prefix match (mask_int)
    '''
   
    network, route, mask_int = entry
    return (route['localpref'], not route['selfOrigin'], len(route['ASPath']), route['origin'], mask_int)
