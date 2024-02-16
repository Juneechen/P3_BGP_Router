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

   
def custom_sort(route):
    ''' 
    route.keys: dict_keys(['network', 'netmask', 'localpref', 'ASPath', 'origin', 'selfOrigin', 'peer']);
    apply multi-level sort based on:
        1. longest prefix match
        2. The entry with the highest localpref wins. If the localprefs are equal…
        3. The entry with selfOrigin as true wins. If all selfOrigins are the equal…
        4. The entry with the shortest ASPath wins. If multiple entries have the shortest length…
        5. The entry with the best origin wins, where IGP > EGP > UNK. If multiple entries have the best origin…
        6. The entry from the neighbor router (i.e., the src of the update message) with the lowest IP address.
    '''
    mask_int = parse_ip(route['netmask'])

    localpref = route['localpref']
    selfOrigin = route["selfOrigin"]
    ASPath_len = len(route['ASPath'])
    origin_preference = {"IGP": 1, "EGP": 2, "UNK": 3}.get(route['origin'])
    peer_ip = route['peer'] # string, cannot negative with - operator

    return (-mask_int, -localpref, -selfOrigin, ASPath_len, origin_preference, peer_ip)

def sort_by_network_and_mask(route):
    ''' 
    route.keys: dict_keys(['network', 'netmask', 'localpref', 'ASPath', 'origin', 'selfOrigin', 'peer']);
    '''
    return (route['network'], route['netmask'])

def aggr_route_pair(route_1, route_2):
    ''' 
    route_a, route_b: dict with keys: ['network', 'netmask', 'localpref', 'ASPath', 'origin', 'selfOrigin', 'peer']
    return the aggregated route if possible, None otherwise
    '''
 
    if (route_1['network'] == route_2['network'] or # same network, can not aggregate
        route_1['localpref'] != route_2['localpref'] or 
        route_1['origin'] != route_2['origin'] or 
        route_1['selfOrigin'] != route_2['selfOrigin'] or 
        route_1['ASPath'] != route_2['ASPath'] or 
        route_1['netmask'] != route_2['netmask'] or 
        route_1['peer'] != route_2['peer']): 
        return None

    ip1_int = parse_ip(route_1['network'])
    ip2_int = parse_ip(route_2['network'])
    mask_int = parse_ip(route_1['netmask']) # a and b have the same netmask

    aggr_mask_int = mask_int & (mask_int - 1) # turn the rightmost 1 to 0, for example, CIDR 19 to 18

    if (ip1_int & aggr_mask_int) != (ip2_int & aggr_mask_int):
        return None
    else: # same prefix after applying the aggr_mask, can aggregate
        new_route = deepcopy(route_1)
        new_route['netmask'] = int_to_ip(aggr_mask_int)
        new_route['network'] = int_to_ip(ip1_int & aggr_mask_int)
        return new_route
        

def aggr_table(table: list):
    ''' 
    table: list of dictionaries with keys: ['network', 'netmask', 'localpref', 'ASPath', 'origin', 'selfOrigin', 'peer']
    return the aggregated table
    '''
    # sort the table so that potential aggregates are next to each other
    table.sort(key=sort_by_network_and_mask)
    aggregated = []

    # loop until no aggregation was made
    while table:
        aggregated = []
        no_aggr = True
        route_1 = table.pop(0)

        while table:
            route_2 = table.pop(0)
            aggr_route = aggr_route_pair(route_1, route_2)
            if aggr_route: # can aggregate
                no_aggr = False
                route_1 = aggr_route
            else: 
                aggregated.append(route_1)
                route_1 = route_2

        aggregated.append(route_1)
        table = aggregated
        if no_aggr:
            break

    return table