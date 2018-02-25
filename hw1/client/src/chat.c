#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "utils.h"
#include "types.h"
#include "protocol.h"

Msg parse_xterm_message(char* buf) {
    Msg msg = {0};
    char *space_loc = strchr(buf, ' ');
    if(space_loc != NULL) {
        *space_loc = 0;
    }

    if (!strcmp(buf, CLIENT_XTERM_QUIT_STR)) {
        msg.command = CLOSE_XTERM;
    } else if (buf[0] == '/') {
        msg.command = INVALID_USER_INPUT;
    } else {
        msg.command = SEND_MESSAGE;
        msg.message = buf;
        msg.outgoing = true;
    }

    return msg;
}


int main(int argc, char *argv[]) {
    sleep(20);
    char *name = argv[1];
    int read_fd = atoi(argv[2]);
    int write_fd = atoi(argv[3]);

    printf("%s, %d, %d \n", name, read_fd, write_fd);

    char *stdin_buf = NULL;
    char *client_buf = NULL;

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
            int n = read_until_terminator(read_fd, &client_buf, END_OF_MESSAGE_SEQUENCE);
            if (n > 0) {
                printf("> %s\n", client_buf);

                free(client_buf);
            }
        }

        // STDIN
        if(poll_fds[1].revents & POLLIN) {
            int n = read_until_terminator(STDIN_FILENO, &stdin_buf, "\n");
            if (n > 0) {
                // print on xterm window
                printf("< %s", stdin_buf);

                Msg msg = parse_xterm_message(stdin_buf);
                // only command we want is /chat
                if(msg.command == CLOSE_XTERM) {
                    exit(EXIT_SUCCESS);
                } else if(msg.command == INVALID_USER_INPUT) {
                    printf("%s\n", "Invalid Command");
                } else {
                    write(write_fd, msg.message, n);
                }

                free(stdin_buf);
            }
        }
    }

    return 0;
}
