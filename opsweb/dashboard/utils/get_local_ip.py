import socket
import fcntl
import struct
from dashboard.utils.wslog import wslog_error,wslog_info

def get_ip_address(ifname):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip_addr = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', ifname[:15].encode("utf8"))
        )[20:24])
    except Exception as e:
        wslog_error().error("获取本机 %s 地址失败，错误信息: %s" %(ifname,e.args))
        ip_addr = '127.0.0.1'
    return ip_addr

if __name__ == '__main__':
    get_ip_address('eth0')