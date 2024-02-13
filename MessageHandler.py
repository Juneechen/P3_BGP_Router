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

        try:
            network = update_msg['msg']['network']
            netmask = update_msg['msg']['netmask']
            ASPath = update_msg['msg']['ASPath']

            self.send_update_to_neighbors(update_msg, srcif)
            self.router.cache_update(update_msg, srcif)
            self.router.update_table(update_msg['msg'], srcif)

            # print('CACHED: ', update_msg)
            # print('----- Updated table ---------', self.router.routing_table)
            
        except KeyError as e:
            print(f'Error processing update message: {e}')
            
    # Inside the Router class
    def send_update_to_neighbors(self, update_msg, srcif):
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
                            'netmask': update_msg['msg']['netmask'],
                            # 'ASPath': [self.router.asn] + update_msg['msg']['ASPath'],
                            'ASPath': [self.router.asn] + update_msg['msg']['ASPath'],
                            'network': update_msg['msg']['network']
                        },
                        'src': self.router.our_addr(neighbor),
                        'dst': neighbor, # Set destination to the neighbor
                        'type': 'update'
                    }
                    self.router.sendJson(neighbor, forwarded_msg)
                    # self.router.send(neighbor, json.dumps(forwarded_msg))   


    def handle_data_message(self, msg: dict, srcif):
        '''
        msg: 
        {'src': '172.168.0.25', 'dst': '192.168.0.25', 'type': 'data', 'msg': {'ignore': 'this'}}
        '''

        print("----- handling DATA message from", self.router.relations.get(srcif), "at", srcif, "-----")

        # identify the destination AS and forward the message to the next hop
        dst = msg['dst']
        next_hop = self.router.get_route(dst) 
        # get_route() returns a single valid match, longest prefix and rules applied in get_route()

        if next_hop: 
            print(f'--------- Forwarding data to {next_hop} for {dst} ----------')
            self.router.sendJson(next_hop, msg)
        else:
            print(f'No route to {dst} found in the routing table')
            no_route_msg = {
                    'src': msg['src'],
                    'dst': dst,
                    'type': 'no route',
                    'msg': {}
                }
            self.router.sendJson(srcif, no_route_msg)



    def handle_dump_message(self, update, srcif):
        print("----- handling DUMP message from", self.router.relations.get(srcif), "at", srcif, "-----")
        # Assuming router.cache is a list of dictionaries containing route announcements
        cached_routes = self.router.cache
        routing_table = self.router.routing_table
        converted_msg = list(routing_table.values())
        print("Routing table:", converted_msg)

        # TODO: Perform aggregation on cached_routes if needed

        # Create the "table" message format
        table_message = {
            "src": update["dst"],          # Change to your router's IP
            "dst": update["src"],
            "type": "table",
            "msg": converted_msg
        }

        # Send the "table" message back to the source router
        self.router.sendJson(srcif, table_message)


    def handle_unknown_message(self, msg, srcif):
        print(f'Received unknown message: {msg} from {srcif}')