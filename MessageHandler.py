#!/usr/bin/env -S python3 -u

import argparse
import socket
import json
import select
import sys
from copy import deepcopy
import utils

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
        # print("----- handling UPDATE message from", self.router.relations.get(srcif), "at", srcif, "-----")
        msg = update_msg['msg']

        try:
            network = msg['network']
            netmask = msg['netmask']
            ASPath = msg['ASPath']

            self.router.cache_update(update_msg, srcif) # cache the complete update msg
            self.router.update_table(msg, srcif) # stores update_msg['msg'] + key "peer" = srcif
            self.send_update_to_neighbors(msg, srcif)
            
        except KeyError as e:
            print(f'Error processing update message: {e}')
            
    def send_update_to_neighbors(self, msg, srcif, msg_type='update'):
        '''sends update or withdraw message to all neighbors except the source'''

        for neighbor, relation in self.router.relations.items():
            if neighbor != srcif: 
                # send if src is customer or neighbor is customer 
                if relation == 'cust' or self.router.relations[srcif] == 'cust':
                    print(f'----- Forwarding update to {relation} at {neighbor} -----')

                    inner_msg = msg 
                    if msg_type == 'update':
                        inner_msg = {'netmask': msg['netmask'],
                                     'ASPath': [self.router.asn] + msg['ASPath'],
                                     'network': msg['network']}
                        
                    forwarded_msg = {
                        'msg': inner_msg,
                        'src': self.router.our_addr(neighbor),
                        'dst': neighbor, # Set destination to the neighbor
                        'type': msg_type
                    }
                    self.router.sendJson(neighbor, forwarded_msg)

    def send_withdraw_to_neighbors(self, msg, srcif):
        # print('UPDATEMSG', update_msg, 'HAHA')

        for neighbor, relation in self.router.relations.items():
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
        next_hop = self.router.get_route(srcif, dst) 
        # get_route() returns a single valid match, longest prefix and rules applied in get_route()

        if next_hop: 
            # print(f'\n--------- Forwarding data to neighbor [{next_hop}], final dst [{dst}] ----------\n')
            self.router.sendJson(next_hop, msg)
        else:
            no_route_msg = {
                    'src': msg['src'],
                    'dst': dst,
                    'type': 'no route',
                    'msg': {}
                }
            self.router.sendJson(srcif, no_route_msg)

    def handle_withdraw_message(self, withdrawal_msg: dict, srcif):
        """
        withdrawal_msg:
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
        """
        
        to_remove = withdrawal_msg['msg']
        
        for each in to_remove:
            network = each['network'] # one of the networks to remove
            routes = self.router.routing_table[network] # all routes for this network
            for route in routes:
                if route['peer'] == srcif:
                    routes.remove(route) # remove route
                    break
            if routes == []:
                del self.router.routing_table[network] # remove key if no routes left

        self.send_update_to_neighbors(to_remove, srcif, 'withdraw')


    def handle_dump_message(self, update, srcif):
        routing_table = self.router.routing_table
        all_routes = list(routing_table.values()) # each value is a list of dictionaries

        # Create the "table" message format
        table_msg = {
            "src": update["dst"],          # Change to my router's IP
            "dst": update["src"],
            "type": "table",
            "msg": []
        }

        for routes_for_one_dst in all_routes:
            table_msg["msg"].extend(routes_for_one_dst)

        # aggregate 
        table_msg["msg"] = utils.aggr_table(table_msg["msg"])

        # Send the "table" message back to the source router
        self.router.sendJson(srcif, table_msg)


    def handle_unknown_message(self, msg, srcif):
        print(f'Received unknown message: {msg} from {srcif}')