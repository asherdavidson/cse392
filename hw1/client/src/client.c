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
    if(signal(SIGPIPE, sig_pipe) == SIG_ERR)
        exit_error("signal error");

    struct pollfd *poll_fds = NULL;

    // init buffers
    char *socket_buf;
    char *stdin_buf;
    char *xterm_buf;

    // Init application state
    ApplicationState app_state = {0};
    app_state.username = username;
    app_state.socket_fd = socket_fd;
    app_state.connection_state = CONNECTING;
    app_state.next_conn = NULL;
    app_state.next_window = NULL;
    // set fds_changed to 1 at the start so it'll be created
    app_state.fds_changed = true;
    app_state.num_fds = 0;

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

        // if number of user client talks to changes, reinit pollfds
        if(app_state.fds_changed) {
            printf("%s\n", "Num FDs changed");
            int num_fds = 2;    // start with 2 for STDIN and socket

            ChatWindow *curr = app_state.next_window;
            while(curr) {
                num_fds++;
                curr = curr->next;
            }

            free(poll_fds);

            poll_fds = calloc(sizeof(struct pollfd), num_fds);
            // socket
            poll_fds[0].fd = socket_fd;
            poll_fds[0].events = POLLIN|POLLPRI;
            // stdin
            poll_fds[1].fd = STDIN_FILENO;
            poll_fds[1].events = POLLIN|POLLPRI;

            curr = app_state.next_window;
            for(int i = 2; i < num_fds; i++, curr = curr->next) {
                poll_fds[i].fd = curr->child_to_parent[0];
                poll_fds[i].events = POLLIN | POLLPRI;
            }

            printf("%s %d\n", "Numfds", num_fds);

            app_state.num_fds = num_fds;
            app_state.fds_changed = false;
        }

        poll(poll_fds, app_state.num_fds, -1);

        // check for socket closed
        if (poll_fds[0].revents & POLLHUP) {
            exit_error("Socket closed");
        }

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

        // xterm windows read
        for(int i = 2; i < app_state.num_fds; i++) {
            if(poll_fds[i].revents & POLLIN) {
                int n = read_until_terminator(poll_fds[i].fd, &xterm_buf, END_OF_MESSAGE_SEQUENCE);
                if (n > 0) {
                    printf("%s\n", xterm_buf);

                    Msg msg = parse_window_message(xterm_buf);
                    process_messsage(&app_state, &msg);

                    free(xterm_buf);
                }
            }
        }
    }

    free(poll_fds);
    // good bye
    close(socket_fd);

    return EXIT_SUCCESS;
}
