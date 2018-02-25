#include <stdbool.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "utils.h"
#include "types.h"
#include "protocol.h"

static volatile bool running = true;

void signal_exit_handler() {
    running = false;
}

Msg parse_xterm_message(char* buf) {
    Msg msg = {0};

    // copy buf to perform strchr on
    size_t len = strlen(buf);
    char *copy = malloc(len + 1);
    strncpy(copy, buf, len + 1);

    char *space_loc = strchr(copy, ' ');
    if(space_loc != NULL) {
        *space_loc = 0;
    }

    if (!strcmp(copy, CLIENT_XTERM_QUIT_STR)) {
        msg.command = XTERM_CLOSE;
    } else if (copy[0] == '/') {
        msg.command = INVALID_USER_INPUT;
    } else {
        msg.command = SEND_MESSAGE;
        msg.message = buf;
        msg.outgoing = true;
    }

    free(copy);
    return msg;
}


Msg parse_client_message(char *buf) {
    Msg msg = {0};
    msg.outgoing = false;

    char* space_loc = strchr(buf, ' ');
    if(space_loc != NULL) {
        *space_loc = 0;
    }

    if(!strcmp(buf, SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST_STR)) {
        msg.command = XTERM_USER_DOES_NOT_EXIST;
    } else if(!strcmp(buf, RECEIVE_MESSAGE_STR)) {
        msg.command = XTERM_USER_MESSAGE;
        // Messages from client should be well formed
        space_loc = strchr(space_loc + 1, ' ');
        *space_loc = 0;

        msg.message = ++space_loc;
    } else {
        msg.command = XTERM_BAD_MSG;
    }

    return msg;
}


void process_xterm_message(Msg* msg, XtermState* state) {
    switch(msg->command) {
        case XTERM_USER_DOES_NOT_EXIST:
            printf("%s\n", "User does not exist");
            break;

        case XTERM_USER_MESSAGE:
            printf("> %s\n", msg->message);
            break;

        case XTERM_CLOSE:
            // reusing signal handler function
            signal_exit_handler();

            break;

        case INVALID_USER_INPUT:
            printf("%s\n", "Invalid Command");
            break;

        case SEND_MESSAGE:
            // TODO send message and process on client side
            printf("< %s\n", msg->message);

            write(state->write_fd, "TO ", 3);
            write(state->write_fd, state->username, strlen(state->username));
            write(state->write_fd, " ", 1);
            write(state->write_fd, msg->message, strlen(msg->message));
            write(state->write_fd, END_OF_MESSAGE_SEQUENCE, END_OF_MESSAGE_SEQUENCE_LENGTH);

            break;

        case XTERM_BAD_MSG:
        default:
            exit_error("bad xterm msg");
            break;
    }
}


int main(int argc, char *argv[]) {
    signal(SIGINT, signal_exit_handler);
    signal(SIGQUIT, signal_exit_handler);
    signal(SIGKILL, signal_exit_handler);
    signal(SIGTERM, signal_exit_handler);
    signal(SIGHUP, signal_exit_handler);

    XtermState state = {0};

    state.username = argv[1];
    state.read_fd = atoi(argv[2]);
    state.write_fd = atoi(argv[3]);

    printf("%s, %d, %d \n", state.username, state.read_fd, state.write_fd);

    char *stdin_buf = NULL;
    char *client_buf = NULL;

    // setup poll
    struct pollfd poll_fds[2];

    poll_fds[0].fd = state.read_fd;
    poll_fds[0].events = POLLIN|POLLPRI;

    poll_fds[1].fd = STDIN_FILENO;
    poll_fds[1].events = POLLIN|POLLPRI;

    while(running) {
        poll(poll_fds, 2, -1);

        if(poll_fds[0].revents & POLLHUP) {
            return 0;
        }

        // Client
        if(poll_fds[0].revents & POLLIN) {
            int n = read_until_terminator(state.read_fd, &client_buf, END_OF_MESSAGE_SEQUENCE);
            if (n > 0) {
                Msg msg = parse_client_message(client_buf);
                process_xterm_message(&msg, &state);
                free(client_buf);
            }
        }

        // STDIN
        if(poll_fds[1].revents & POLLIN) {
            int n = read_until_terminator(STDIN_FILENO, &stdin_buf, "\n");
            if (n > 0) {
                Msg msg = parse_xterm_message(stdin_buf);
                process_xterm_message(&msg, &state);
                free(stdin_buf);
            }
        }
    }

    // let client know we are exiting and give username to help cleanup
    write(state.write_fd, XTERM_EXIT_STR, 5);
    write(state.write_fd, " ", 1);
    write(state.write_fd, state.username, strlen(state.username));
    write(state.write_fd, END_OF_MESSAGE_SEQUENCE, END_OF_MESSAGE_SEQUENCE_LENGTH);

    close(state.read_fd);
    close(state.write_fd);

    return 0;
}
