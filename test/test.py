import socket
import psutil


def get_wireless_lan_ip():
    for interface_name, interface_addresses in psutil.net_if_addrs().items():
        if any(x in interface_name for x in ['Wireless', 'Wi-Fi']):
            for address in interface_addresses:
                if address.family in (socket.AF_INET, socket.AF_INET6):
                    return address.address
    return ""

# Call the function and print the result
print(get_wireless_lan_ip())
