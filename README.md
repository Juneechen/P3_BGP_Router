# BGP Router Project

## Overview

This project involves the implementation of a BGP (Border Gateway Protocol) router. The router is designed to handle BGP protocol messages, update forwarding tables, withdrawing messages and forward data packets in a simulated network environment.

## Getting Started

### Prerequisites

- Python 3.x (for starter code)
- Socket Programming

### Simulator
The simulator is provided to test the BGP router in a controlled environment. It creates neighboring routers, establishes connections, and runs your router program with specified command line arguments. The simulator includes a suite of configuration files in the configs/ directory.

To run the simulator:

```bash
./run configs/<config-file>
```

### Project Structure

- 4700router: Main program implementing the BGP router.
- configs/: Configuration files for the simulator.
- tests/: Additional test cases.
- Command Line Specification
```bash
./4700router <asn> <port-ip.add.re.ss-[peer,prov,cust]> [port-ip.add.re.ss-[peer,prov,cust]]
```

# Router Functionality

## Accept BGP Messages

The router is designed to accept the following BGP messages from its neighbors:

- **Route Update Messages:**
  - Accepts route update messages containing information about reachable networks.
  - Saves a copy of the update for future reference.
  - Adds an entry to the forwarding table based on the received update.
  - Potentially sends copies of the update to other neighbors based on BGP relationship rules.

- **Route Revocation Messages:**
  - Accepts route revocation messages indicating the withdrawal of previously announced routes.
  - Saves a copy of the revocation for future reference.
  - Removes the corresponding entry from the forwarding table.
  - May send copies of the revocation to other neighbors based on BGP relationship rules.

## Forward Data Packets

The router forwards data packets towards their correct destination based on the information in its forwarding table.

- **Data Messages:**
  - Receives data packets with source and destination IP addresses.
  - Determines the best route in the forwarding table for the destination IP.
  - Forwards the data packet on the appropriate port if a valid route is found.
  - Handles cases where there is no route to the destination, sending a "no route" error message back to the source.

## Error Handling

The router is responsible for returning error messages in cases where a data packet cannot be delivered.

- **No Route Messages:**
  - If the router cannot find a route for a given data packet destination, it sends a "no route" error message back to the source.

## Table Coalescing

The router coalesces forwarding table entries for adjacent networks on the same port.

- **Aggregation:**
  - Aggregates entries for adjacent networks that have the same next-hop router and similar attributes.
  - Performs aggregation after each route update to compress the table.
  - May need to disaggregate the table in response to route withdrawal messages.

## Serialization for Correctness Checking

The router serializes its routing table cache for correctness checking.

- **Dump and Table Messages:**
  - Responds to "dump" messages from the simulator by providing a "table" message.
  - The "table" message includes a serialized copy of the current routing announcement cache.
  - Aggregates entries in the cache to provide a concise and accurate representation.


## Challanges Faced:

- Choosing the right data structure for the forwarding table is crucial for efficient route lookups and updates. Ended up with alist of JSON objects for fast lookup and restructuring it to a table during the dump, aggregation processes.
- Choosing the right time to aggregate. In favour of performance during update, data messages, aggregate is performed in a lazy fashion ie: it happens when the router is expected to dump the routing table. 


