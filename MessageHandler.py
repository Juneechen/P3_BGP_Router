#!/usr/bin/env -S python3 -u

import argparse
import socket
import json
import select
import sys

class MessageHandler:
    """ Class to handle the messages received by the AS and processing them based on their type
    """
    def __init__(self, router):
        self.router = router

    def handle_message(self, msg, srcif):
        try:
            parsed_msg = json.loads(msg)
            msg_type = parsed_msg.get("type")

            if msg_type:
                # Call the corresponding method based on the message type
                print("HERE", msg_type)
                method_name = f"handle_{msg_type}_message"
                handler_method = getattr(self, method_name, self.handle_unknown_message)
                handler_method(parsed_msg, srcif)
            else:
                print("Received message with no type:", msg)

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")

    def handle_update_message(self, update_msg, srcif):
        try:
            network = update_msg["msg"]["network"]
            netmask = update_msg["msg"]["netmask"]
            ASPath = update_msg["msg"]["ASPath"]

            print(f"Received update for network {network}/{netmask} via {srcif} with ASPath {ASPath}")
            print("RELATIONS", self.router.relations.get(srcif))
            if self.router.relations.get(srcif) == "cust":
                self.send_update_to_neighbors(update_msg, srcif)

        except KeyError as e:
            print(f"Error processing update message: {e}")
            
    # Inside the Router class
    def send_update_to_neighbors(self, update_msg, srcif):
        print("UPDATEMSG", update_msg, "HAHA")
        for neighbor, relation in self.router.relations.items():
            print("NEIGHBOR:", neighbor, "RELATION:", relation)
            if neighbor != srcif:
                if relation == "cust" or (relation in ["peer", "prov"] and self.relations[srcif] == "cust"):
                    # aspath = [self.router.asn] + update_msg["msg"]["ASPath"]
                    # as_path_str = ",".join(map(str, [self.router.asn] + update_msg["msg"]["ASPath"]))
                    # as_path_str = f"[{self.router.asn}," + ",".join(map(str, update_msg["msg"]["ASPath"])) + "]"
                    # print(aspath,"PATH")
                    forwarded_msg = {
                        "msg": {
                            "netmask": update_msg["msg"]["netmask"],
                            # "ASPath": [self.router.asn] + update_msg["msg"]["ASPath"],
                            "ASPath": [4] + update_msg["msg"]["ASPath"],
                            "network": update_msg["msg"]["network"]
                        },
                        "src": self.router.our_addr(neighbor),
                        "dst": neighbor, # Set destination to the neighbor
                        "type": "update"
                    }
                    self.router.sendJson(neighbor, forwarded_msg)
                    print(f"Sent update to {neighbor}")


    def handle_data_message(self, update, srcif):
        #TODO: Implement data message
        pass


    def handle_unknown_message(self, msg, srcif):
        print(f"Received unknown message: {msg} from {srcif}")