#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <poll.h>
#include <netdb.h>
#include <signal.h>
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

    // install signal handler
    if(signal(SIGCHLD, sig_child) == SIG_ERR)
        exit_error("signal error");

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
    char *stdin_buf;

    // Init application state
    ApplicationState app_state = {0};
    app_state.username = username;
    app_state.socket_fd = socket_fd;
    app_state.connection_state = CONNECTING;

    // start handshake
    // create message
    Msg connect = {0};
    connect.command = CONNECT;
    connect.outgoing = true;
    // send message
    send_message(&app_state, connect);

    while (true) {
        if (app_state.connection_state == TERMINATE)
            break;

        poll(poll_fds, 2, -1);

        // socket read
        if (poll_fds[0].revents & POLLIN) {
            // debug("socket in");

            // blocks until double newlines
            int n = read_until_terminator(socket_fd, &socket_buf, END_OF_MESSAGE_SEQUENCE);
            if (n > 0) {
                Msg msg = parse_server_message(socket_buf);
                process_messsage(&app_state, &msg);

                // cleanup
                free(socket_buf);
                free(msg.buf);
            }
        }

        // stdin read
        if (app_state.connection_state == LOGGED_IN
            && poll_fds[1].revents & POLLIN) {
            // debug("stdin in");

            int n = read_until_terminator(STDIN_FILENO, &stdin_buf, "\n");
            if (n > 0) {
                Msg msg = parse_user_message(stdin_buf);
                process_messsage(&app_state, &msg);

                free(stdin_buf);

            }
        }
    }

    // good bye
    close(socket_fd);

    return EXIT_SUCCESS;
}