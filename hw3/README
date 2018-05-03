# Fuse Instructions

## Bootstrap

example:
`python3 bootstrap.py -l localhost -p 8000`

```
usage: bootstrap.py [-h] [-l HOST] [-p PORT]

optional arguments:
  -h, --help            show this help message and exit
  -l HOST, --host HOST  IP to serve from
  -p PORT, --port PORT  Port number to listen on (default 8000)
```


## Client

example:
`python client.py localhost 8001 fuse .fuse -p 8081`

```
usage: client.py [-h] [-p PORT]
                 bootstrap_addr bootstrap_port mount_point local_files

positional arguments:
  bootstrap_addr        Boot strap node address
  bootstrap_port        Boot strap node port
  mount_point           FUSE mount point
  local_files           FUSE local file cache

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  Server port (default 8080)
```

## In the event consistent hashing blows up
The base version is located at the HEAD of master.
