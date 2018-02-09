#include <sys/types.h>
#include <sys/socket.h>
// #include <sys/epoll.h>
#include <sys/ioctl.h>
#include <poll.h>
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

void debug(char *msg) {
    printf("\x1B[1;34m%s\x1B[0m\n", msg);
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

int main(int argc, char *argv[])
{
    int verboseFlag = 0;
    char *username = NULL;
    char *address = NULL;
    char *port = NULL;
    int c;
    int opterr = 0;

    char *helpMsg =
        "./client [-hv] NAME SERVER_IP SERVER_PORT\n" \
        "-h                         Displays this help menu, and returns EXIT_SUCCESS.\n" \
        "-v                         Verbose print all incoming and outgoing protocol verbs & content.\n" \
        "NAME                       This is the username to display when chatting.\n" \
        "SERVER_IP                  The ip address of the server to connect to.\n" \
        "SERVER_PORT                The port to connect to.\n";

    while((c = getopt(argc, argv, "hv")) != -1) {
        switch(c) {
            case 'h':
                printf("%s", helpMsg);
                exit(EXIT_SUCCESS);
            case 'v':
                verboseFlag = 1;
                break;
            default:
                exit_error(helpMsg);
        }
    }

    if(optind >= argc) {
        exit_error(helpMsg);
    }

    // TODO: more error checking
    username = argv[optind];
    address = argv[optind + 1];
    port = argv[optind + 2];

    // get socket connection
    int socket_fd = init_socket(address, port);

    // init poll fds
    struct pollfd poll_fds[3];
    // socket
    poll_fds[0].fd = socket_fd;
    poll_fds[0].events = POLLIN;
    // stdin
    poll_fds[1].fd = STDIN_FILENO;
    poll_fds[1].events = POLLIN;
    // stdout
    poll_fds[2].fd = STDOUT_FILENO;
    poll_fds[2].events = POLLOUT;

    char in_buf[BUF_SIZE];
    char out_buf[BUF_SIZE];
    memset(&in_buf, 0, sizeof(in_buf));
    memset(&out_buf, 0, sizeof(out_buf));

    int cnt = 0;

    while (1) {
        int n_events = poll(poll_fds, 3, -1);

        // socket read
        if (poll_fds[0].revents & POLLIN) {
            // debug("socket in");

            memset(&out_buf, 0, sizeof(out_buf));
            if (ioctl(socket_fd, FIONREAD, &cnt) == 0 && cnt > 0) {
                int n = read(socket_fd, &out_buf, BUF_SIZE);
                write(STDOUT_FILENO, &out_buf, n);
            }
        }

        if (poll_fds[1].revents & POLLIN) {
            // debug("stdin in");

            memset(&in_buf, 0, sizeof(in_buf));
            if (ioctl(STDIN_FILENO, FIONREAD, &cnt) == 0 && cnt > 0) {
                int n = read(STDIN_FILENO, &in_buf, BUF_SIZE);
                write(socket_fd, &in_buf, n);
            }

        }

        if (poll_fds[2].revents & POLLOUT) {
            // debug("stdout out");

        }
    }


    // good bye
    close(socket_fd);

    return EXIT_SUCCESS;
}