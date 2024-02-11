#!/usr/bin/env -S python3 -u

import argparse
import socket
import json
import select
import sys

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
                # print('HERE', msg_type)
                method_name = f'handle_{msg_type}_message'
                handler_method = getattr(self, method_name, self.handle_unknown_message)
                handler_method(parsed_msg, srcif)
            else:
                print('Received message with no type:', msg)

        except json.JSONDecodeError as e:
            print(f'Error decoding JSON: {e}')

    def handle_update_message(self, update_msg, srcif):
        print("----- handling UPDATE message from", self.router.relations.get(srcif), "at", srcif, "-----")

        try:
            network = update_msg['msg']['network']
            netmask = update_msg['msg']['netmask']
            ASPath = update_msg['msg']['ASPath']

            # print(f'Received update for network {network}/{netmask} via {srcif} with ASPath {ASPath}')
            # print('RELATIONS', self.router.relations.get(srcif))
            
            # # only sending update to neighbors if the source is a customer:
            # if self.router.relations.get(srcif) == 'cust':
            #     self.send_update_to_neighbors(update_msg, srcif)

            # should probably send msg from any neighbor to customer as well
            self.send_update_to_neighbors(update_msg, srcif)

            # TODO: cache the update message
            self.router.cache_update(update_msg, srcif)
            
            self.router.update_table(network, netmask, srcif, update_msg['msg']['localpref'], ASPath)
            
                

        except KeyError as e:
            print(f'Error processing update message: {e}')
            
    # Inside the Router class
    def send_update_to_neighbors(self, update_msg, srcif):
        # print('UPDATEMSG', update_msg, 'HAHA')

        for neighbor, relation in self.router.relations.items():
            # print('NEIGHBOR:', neighbor, 'RELATION:', relation)
            # may send update to all neighbors except the source
            if neighbor != srcif: 
                # if relation == 'cust' or (relation in ['peer', 'prov'] and self.relations[srcif] == 'cust'):

                # send if src is customer or neighbor is customer 
                if relation == 'cust' or self.router.relations[srcif] == 'cust':
                    print(f'----- Forwarding update to {relation} at {neighbor} -----')
                    # aspath = [self.router.asn] + update_msg['msg']['ASPath']
                    # as_path_str = ','.join(map(str, [self.router.asn] + update_msg['msg']['ASPath']))
                    # as_path_str = f'[{self.router.asn},' + ','.join(map(str, update_msg['msg']['ASPath'])) + ']'
                    # print(aspath,'PATH')
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
                    # print(f'Sent update to {neighbor}')

                    # self.router.send(neighbor, json.dumps(forwarded_msg))   
                    print("----- Forwarding completed -----")


    def handle_data_message(self, msg: dict, srcif):
        '''
        msg: 
        {'src': '172.168.0.25', 'dst': '192.168.0.25', 'type': 'data', 'msg': {'ignore': 'this'}}
        '''

        print("----- handling DATA message from", self.router.relations.get(srcif), "at", srcif, "-----")

        # Tidentify the destination AS and forward the message to the next hop

        dst = msg['dst']
        next_hop = self.router.get_route(dst) 
        if next_hop:
            # TODO: apply rules (check relationship, etc.)
            print(f'Forwarding data to {next_hop} for {dst}')
            self.router.sendJson(next_hop, msg)
        else:
            print(f'No route to {dst} found in the routing table')



    def handle_dump_message(self, update, srcif):
        print("----- handling DUMP message from", self.router.relations.get(srcif), "at", srcif, "-----")

        self.router.sendJson(srcif, self.router.cache)
        # TODO: fix dump msg format


    def handle_unknown_message(self, msg, srcif):
        print(f'Received unknown message: {msg} from {srcif}')