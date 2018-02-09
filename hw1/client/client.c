#include <sys/types.h>
#include <sys/socket.h>
#include <sys/epoll.h>
#include <sys/ioctl.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#define BUF_SIZE 500
#define MAX_EVENTS 10

void exit_error(char *msg) {
    printf("\x1B[1;31m%s\x1B[0m\n", msg);
    exit(EXIT_FAILURE);
}


int init_socket(const char *address, const char *port) {
    struct addrinfo hints;
    struct addrinfo *result;

    // zero out and write our hints
    memset(&hints, 0, sizeof(struct addrinfo));
    hints.ai_family = AF_INET; // TODO: ipv6 support?
    hints.ai_socktype = SOCK_STREAM;

    // get the linked-list of results
    if (getaddrinfo(address, port, &hints, &result) != 0) {
        exit_error("error in getaddrinfo");
    }

    struct addrinfo *next;
    int fd;

    // find the first valid result
    for (next = result; next != NULL; next = next->ai_next) {
        // try to open a socket
        fd = socket(result->ai_family, result->ai_socktype, result->ai_protocol);

        if (fd == -1) continue; // bad socket!

        // connection okay!
        if (connect(fd, result->ai_addr, result->ai_addrlen) != -1) break;

        // socket didn't connect, so close it to be safe
        close(fd);
    }

    // didn't find a socket
    if (next == NULL) {
        exit_error("No valid address found");
    }

    // cleanup
    freeaddrinfo(result);

    return fd;

}


int main(int argc, char const *argv[])
{
    // TODO: handle arguments!
    if (argc != 4) {
        exit_error("invalid args");
    }

    // args
    const char *address = argv[2];
    const char *port = argv[3];
    
    // get socket connection
    int socket_fd = init_socket(address, port);






    // create epoll multiplexer
    int epoll_fd = epoll_create1(0);
    if (epoll_fd == -1) {
        exit_error("error creating epoll");
    }

    // socket read/write event
    struct epoll_event socket_event;
    memset(&socket_event, 0, sizeof(struct epoll_event));
    socket_event.events = EPOLLIN;
    socket_event.data.fd = socket_fd;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, socket_fd, &socket_event) == -1) {
        exit_error("Error adding socket fd to epoll");
    }

    // stdin read event
    struct epoll_event stdin_event;
    memset(&stdin_event, 0, sizeof(struct epoll_event));
    stdin_event.events = EPOLLIN;
    stdin_event.data.fd = STDIN_FILENO;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, STDIN_FILENO, &stdin_event) == -1) {
        exit_error("Error adding stdin fd to epoll");
    }

    // stdout read event
    struct epoll_event stdout_event;
    memset(&stdout_event, 0, sizeof(struct epoll_event));
    stdout_event.events = EPOLLOUT;
    stdout_event.data.fd = STDOUT_FILENO;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, STDOUT_FILENO, &socket_event) == -1) {
        exit_error("Error adding stdout fd to epoll");
    }

    char buf[BUF_SIZE];
    memset(&buf, 0, sizeof(buf));

    struct epoll_event events[MAX_EVENTS];
    memset(&events, 0, sizeof(events));

    int cnt;

    while(1) {
        int n_events = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        if (n_events == -1) {
            exit_error("error in epoll_wait");
        }

        for (int i = 0; i < n_events; i++) {
            // socket_fd event
            if (events[i].data.fd == socket_fd) {
                if (events[i].events & EPOLLIN) {
                    printf("%s\n", "socket_fd EPOLLIN");

                    ioctl(socket_fd, FIONREAD, &cnt);
                    if (cnt > 0) {
                        int n = read(socket_fd, &buf, sizeof(buf));
                        write(STDOUT_FILENO, buf, n);                        
                    }
                
                } else if (events[i].events & EPOLLOUT) {
                    printf("%s\n", "socket_fd EPOLLOUT");
                }

                // printf("%s\n", "socket ready");

            // stdin event
            } else if (events[i].data.fd == STDIN_FILENO) {
                printf("%s\n", "stdin ready");
                int n = read(STDIN_FILENO, &buf, sizeof(buf));
                write(socket_fd, buf, n);

            // stdout event
            } else if (events[i].data.fd == STDOUT_FILENO) {
                printf("%s\n", "stdout ready");

            }
        }
    }





    // // historic first words
    // write(socket_fd, "hello\n", 7);

    // // they respond
    // read(socket_fd, &buf, sizeof(buf));

    // printf("%s\n", buf);

    // good bye
    close(socket_fd);

    return EXIT_SUCCESS;
}