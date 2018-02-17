#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <poll.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <stdbool.h>

#include "types.h"
#include "utils.h"
#include "protocol.h"


int main(int argc, char *argv[]) {
    int verboseFlag = 0;
    char *username = NULL;
    char *address = NULL;
    char *port = NULL;

    parseArgs(argc, argv, &verboseFlag, &username, &address, &port);

    // get socket connection
    int socket_fd = init_socket(address, port);

    // init poll fds
    struct pollfd poll_fds[2];
    // socket
    poll_fds[0].fd = socket_fd;
    poll_fds[0].events = POLLIN|POLLPRI;
    // stdin
    poll_fds[1].fd = STDIN_FILENO;
    poll_fds[1].events = POLLIN|POLLPRI;

    // init buffers
    char *socket_buf;
    char stdin_buf[BUF_SIZE];
    memset(&stdin_buf, 0, sizeof(stdin_buf));

    // Init application state
    ApplicationState app_state = {0};
    app_state.username = username;
    app_state.socket_fd = socket_fd;
    app_state.connection_state = CONNECTING;

    // start handshake
    // create message
    Msg connect = {0};
    connect.command = CONNECT;
    // send message
    send_message(socket_fd, connect);

    while (true) {
        if (app_state.connection_state == TERMINATE)
            break;

        poll(poll_fds, 2, -1);

        // socket read
        if (poll_fds[0].revents & POLLIN) {
            // debug("socket in");

            // blocks until double newlines
            int n = read_until_newlines(socket_fd, &socket_buf);
            if (n > 0) {
                Msg msg = parse_server_message(socket_buf);
                process_messsage(&app_state, &msg);

                // cleanup
                free(socket_buf);
                free(msg.buf);
            }
        }

        if (poll_fds[1].revents & POLLIN) {
            // debug("stdin in");

            memset(&stdin_buf, 0, sizeof(stdin_buf));
            int cnt;
            if (ioctl(STDIN_FILENO, FIONREAD, &cnt) == 0 && cnt > 0) {
                int n = read(STDIN_FILENO, &stdin_buf, BUF_SIZE);

                write(socket_fd, stdin_buf, n);
                write(socket_fd, END_OF_MESSAGE_SEQUENCE, strlen(END_OF_MESSAGE_SEQUENCE));
            }

        }
    }


    // good bye
    close(socket_fd);

    return EXIT_SUCCESS;
}