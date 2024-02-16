from copy import deepcopy

def parse_ip(ip):
    ''' 
    ip in dotted decimal notation to integer
    '''
    return sum(int(x) << (24 - i * 8) for i, x in enumerate(ip.split('.')))

def int_to_ip(ip_int):
    ''' 
    ip in integer to dotted decimal notation
    '''
    return '.'.join(str((ip_int >> (24 - i * 8)) & 0xFF) for i in range(4))

   
def custom_sort(entry):
    ''' 
    entry tuple: (network, route, mask_int);
    route.keys: dict_keys(['network', 'netmask', 'localpref', 'ASPath', 'origin', 'selfOrigin', 'peer']);
    apply multi-level sort based on:
        1. The entry with the highest localpref wins. If the localprefs are equal…
        2. The entry with selfOrigin as true wins. If all selfOrigins are the equal…
        3. The entry with the shortest ASPath wins. If multiple entries have the shortest length…
        4. The entry with the best origin wins, where IGP > EGP > UNK. If multiple entries have the best origin…
        5. The entry from the neighbor router (i.e., the src of the update message) with the lowest IP address.
        6. Using these rules (plus the longest prefix match rule above)
    '''
    network, route, mask_int = entry

    localpref = route['localpref']
    selfOrigin = route["selfOrigin"]
    ASPath_len = len(route['ASPath'])
    origin_preference = {"IGP": 1, "EGP": 2, "UNK": 3}.get(route['origin'])
    peer_ip = route['peer'] # string, cannot negative with - operator

    return (-localpref, -selfOrigin, ASPath_len, origin_preference, peer_ip, -mask_int)

def aggr_route_pair(a, b):
    ''' 
    route_a, route_b: dict with keys: ['network', 'netmask', 'localpref', 'ASPath', 'origin', 'selfOrigin', 'peer']
    return the aggregated route if possible, None otherwise
    '''
 
    if (a['network'] == b['network'] or # same network, can not aggregate
        a['localpref'] != b['localpref'] or 
        a['origin'] != b['origin'] or 
        a['selfOrigin'] != b['selfOrigin'] or 
        a['ASPath'] != b['ASPath'] or 
        a['netmask'] != b['netmask'] or 
        a['peer'] != b['peer']): 
        return None

    ip1_int = parse_ip(a['network'])
    ip2_int = parse_ip(b['network'])
    mask_int = parse_ip(a['netmask']) # a and b have the same netmask
    aggr_mask_int = mask_int & (mask_int - 1) # turn the rightmost 1 to 0, for example, CIDR 19 to 18

    if (ip1_int & aggr_mask_int) != (ip2_int & aggr_mask_int):
        return None
    else:
        new_route = deepcopy(a)
        new_route['netmask'] = int_to_ip(aggr_mask_int)
        new_route['network'] = int_to_ip(ip1_int & aggr_mask_int)
        return new_route
        

        
