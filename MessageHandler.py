#!/usr/bin/env -S python3 -u

import argparse
import socket
import json
import select
import sys
from copy import deepcopy

class MessageHandler:
    ''' Class to handle the messages received by the AS and processing them based on their type
    '''
    def __init__(self, router):
        self.router = router

    def handle_message(self, msg, srcif):
        try:
            parsed_msg = json.loads(msg)
            msg_type = parsed_msg.get('type')

            if msg_type:
                # Call the corresponding method based on the message type
                method_name = f'handle_{msg_type}_message'
                handler_method = getattr(self, method_name, self.handle_unknown_message)
                handler_method(parsed_msg, srcif)
            else:
                print(f'-------- Received message with no type: {msg} ---------')

        except json.JSONDecodeError as e:
            print(f'Error decoding JSON: {e}')

    def handle_update_message(self, update_msg, srcif):
        print("----- handling UPDATE message from", self.router.relations.get(srcif), "at", srcif, "-----")

        msg = update_msg['msg']

        try:
            network = msg['network']
            netmask = msg['netmask']
            ASPath = msg['ASPath']

            self.router.cache_update(update_msg, srcif) # cache the complete update msg
            self.router.update_table(msg, srcif) # stores update_msg['msg'] + key "peer" = srcif
            self.send_update_to_neighbors(msg, srcif)

            # print('CACHED: ', update_msg)
            # print('----- Updated table ---------', self.router.routing_table)
            
        except KeyError as e:
            print(f'Error processing update message: {e}')
            
    # Inside the Router class
    def send_update_to_neighbors(self, msg, srcif):
        # print('UPDATEMSG', update_msg, 'HAHA')

        for neighbor, relation in self.router.relations.items():
            # print('NEIGHBOR:', neighbor, 'RELATION:', relation)
            # might send update to all neighbors except the source
            if neighbor != srcif: 
                # send if src is customer or neighbor is customer 
                if relation == 'cust' or self.router.relations[srcif] == 'cust':
                    print(f'----- Forwarding update to {relation} at {neighbor} -----')

                    forwarded_msg = {
                        'msg': {
                            'netmask': msg['netmask'],
                            # 'ASPath': [self.router.asn] + update_msg['msg']['ASPath'],
                            'ASPath': [self.router.asn] + msg['ASPath'],
                            'network': msg['network']
                        },
                        'src': self.router.our_addr(neighbor),
                        'dst': neighbor, # Set destination to the neighbor
                        'type': 'update'
                    }
                    self.router.sendJson(neighbor, forwarded_msg)

    def send_withdraw_to_neighbors(self, msg, srcif):
        # print('UPDATEMSG', update_msg, 'HAHA')

        for neighbor, relation in self.router.relations.items():
            # print('NEIGHBOR:', neighbor, 'RELATION:', relation)
            # might send update to all neighbors except the source
            if neighbor != srcif: 
                # send if src is customer or neighbor is customer 
                if relation == 'cust' or self.router.relations[srcif] == 'cust':
                    print(f'----- Forwarding withdraw to {relation} at {neighbor} -----')
                    msg["src"] = self.router.our_addr(neighbor)
                    msg["dst"] = neighbor
                    self.router.sendJson(neighbor, msg)


    def handle_data_message(self, msg: dict, srcif):
        '''
        msg: 
        {'src': '172.168.0.25', 'dst': '192.168.0.25', 'type': 'data', 'msg': {'ignore': 'this'}}
        '''


        # identify the destination AS and forward the message to the next hop
        dst = msg['dst']
        next_hop = self.router.get_route(dst) 
        # get_route() returns a single valid match, longest prefix and rules applied in get_route()

        # print(f"----- handling DATA message from {self.router.relations.get(srcif)} at {srcif}, final dst [{dst}] ------")

        if next_hop: 
            # print(f'\n--------- Forwarding data to neighbor [{next_hop}], final dst [{dst}] ----------\n')
            self.router.sendJson(next_hop, msg)
        else:
            print(f'No route to {dst} found in the routing table')
            no_route_msg = {
                    'src': msg['src'],
                    'dst': dst,
                    'type': 'no route',
                    'msg': {}
                }
            print("NO ROUTE")
            self.router.sendJson(srcif, no_route_msg)

    def handle_withdraw_message(self, withdrawal_msg: dict, srcif):
        """_summary_
        {
            "src":  "<source IP>",        # Example: 172.65.0.2
            "dst":  "<destination IP>",   # Example: 172.65.0.1
            "type": "withdraw",                   
            "msg": 
            [
                {"network": "<network prefix>", "netmask": "<associated subnet mask>"},
                {"network": "<network prefix>", "netmask": "<associated subnet mask>"},
                ...
            ]
        }

        Args:
            msg (dict): _description_
            srcif (_type_): _description_
        """
        print("----- handling WITHDRAW message from", self.router.relations.get(srcif), "at", srcif, "-----")
        source = withdrawal_msg["src"]
        destination = withdrawal_msg["dst"]
        print("SRC DST", source, " - ", destination)

        entries_to_complete_remove = []

        for entry in withdrawal_msg["msg"]:
            network = entry["network"]
            netmask = entry["netmask"]
            for network in self.router.routing_table:
                # Filter out entries matching the withdrawn network and netmask
                self.router.routing_table[network] = [path for path in self.router.routing_table[network] if path.get("netmask") != netmask]
                print("HERE", network)
                # Remove the network key if no paths remain
                if not self.router.routing_table[network]:
                    print("DELETING",network)
                    entries_to_complete_remove.append(network)
        
        # Remove the entries outside the loop to avoid dictionary size change during iteration
        for entry in entries_to_complete_remove:
            if entry in self.router.routing_table:
                del self.router.routing_table[entry]
        
        self.send_withdraw_to_neighbors(withdrawal_msg, srcif)

        return

    def handle_dump_message(self, update, srcif):
        print("----- handling DUMP message from", self.router.relations.get(srcif), "at", srcif, "-----")
        # Assuming router.cache is a list of dictionaries containing route announcements
        cached_routes = self.router.cache
        routing_table = self.router.routing_table
        # converted_msg = list(routing_table.values()) 
        all_routes = list(routing_table.values()) # each value is a list of dictionaries

        # print("Routing table:", all_routes)

        # TODO: per instruction: need to perform aggregation (see next section) on these announcements before you send your response.

        # Create the "table" message format
        table_msg = {
            "src": update["dst"],          # Change to your router's IP
            "dst": update["src"],
            "type": "table",
            "msg": []
        }

        for routes_for_one_dst in all_routes:
            table_msg["msg"].extend(routes_for_one_dst)

        # Send the "table" message back to the source router
        self.router.sendJson(srcif, table_msg)


    def handle_unknown_message(self, msg, srcif):
        print(f'Received unknown message: {msg} from {srcif}')