#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "../utils.h"
#include "../types.h"

int main(int argc, char *argv[]) {
    char *name = argv[1];
    int read_fd = atoi(argv[2]);
    int write_fd = atoi(argv[3]);

    printf("%s, %d, %d \n", name, read_fd, write_fd);

    // setup poll

    struct pollfd poll_fds[2];

    poll_fds[0].fd = read_fd;
    poll_fds[0].events = POLLIN|POLLPRI;

    poll_fds[1].fd = STDIN_FILENO;
    poll_fds[1].events = POLLIN|POLLPRI;

    while(true) {
        poll(poll_fds, 2, -1);

        if(poll_fds[0].revents & POLLHUP) {
            return 0;
        }

        // Client
        if(poll_fds[0].revents & POLLIN) {
            char buffer[512];
            int n;
            while((n = read(read_fd, buffer, 512)) > 0) {
                write(STDOUT_FILENO, buffer, n);
            }
        }

        // STDIN
        if(poll_fds[1].revents & POLLIN) {
            char buffer[512];
            int n;
            while((n = read(STDIN_FILENO, buffer, 512)) > 0) {
                write(STDOUT_FILENO, buffer, n);
            }
        }
    }

    return 0;
}
