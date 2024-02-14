def parse_ip(ip):
    ''' 
    ip in dotted decimal notation to integer
    '''
    return sum(int(x) << (24 - i * 8) for i, x in enumerate(ip.split('.')))

   
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

        
