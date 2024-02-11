def parse_ip(ip):
    ''' 
    ip in dotted decimal notation to integer
    '''
    return sum(int(x) << (24 - i * 8) for i, x in enumerate(ip.split('.')))