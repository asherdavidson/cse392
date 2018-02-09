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


int main(int argc, char const *argv[])
{
    // TODO: handle arguments!
    if (argc != 4) {
        exit_error("invalid args");
    }
    
    // get the address
    struct addrinfo hints;
    struct addrinfo *result;

    memset(&hints, 0, sizeof(struct addrinfo));
    hints.ai_family = AF_INET; // TODO: ipv6 support?
    hints.ai_socktype = SOCK_STREAM;

    if (getaddrinfo(argv[2], argv[3], &hints, &result) != 0) {
        exit_error("error in getaddrinfo");
    }

    struct addrinfo *next;
    int fd;

    for (next = result; next != NULL; next = next->ai_next) {
        fd = socket(result->ai_family, result->ai_socktype, result->ai_protocol);

        if (fd == -1) continue;

        if (connect(fd, result->ai_addr, result->ai_addrlen) != -1) break;

        close(fd);
    }

    if (next == NULL) {
        exit_error("No valid address found");
    }

    freeaddrinfo(result);

    write(fd, "hello\n", 7);

    char buf[BUF_SIZE];
    memset(&buf, 0, sizeof(buf));
    read(fd, &buf, sizeof(buf));

    printf("%s\n", buf);

    close(fd);

    


    return 0;
}