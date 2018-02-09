#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#define BUF_SIZE 500

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
    int fd = init_socket(address, port);

    // historic first words
    write(fd, "hello\n", 7);

    // they respond
    char buf[BUF_SIZE];
    memset(&buf, 0, sizeof(buf));
    read(fd, &buf, sizeof(buf));

    printf("%s\n", buf);

    // good bye
    close(fd);

    return EXIT_SUCCESS;
}