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

void exit_error(char *msg) {
    printf("\x1B[1;31m%s\x1B[0m\n", msg);
    exit(EXIT_FAILURE);
}

void debug(char *msg) {
    printf("\x1B[1;34m%s\x1B[0m\n", msg);
}

int parse_user_list(char* buf, char*** users) {
    // find the number of users
    int num_users = 0;
    char *buf_ptr = buf;
    while (buf_ptr = strchr(buf_ptr, ' ')) {
        num_users++;
        buf_ptr++;
    }

    int n = 0;
    char* delim = " ";
    *users = calloc(sizeof(char*), num_users+1); // ends with null-terminator

    char* token = strtok(buf, delim);

    while(token != NULL) {
        (*users)[n++] = token;
        token = strtok(NULL, delim);
    }

    return n;
}

/*
 * NOTE: we can just call read twice passing in the terminating string
 * on the second call
 *
 * Given a string, return another string with protocol termination sequence
*/
char *terminate_strn(char* str, size_t len) {
    // len should not include null terminator
    char* term_str = malloc(len + 5);
    strncpy(term_str, str, len);
    strncpy(term_str + (char)len, END_OF_MESSAGE_SEQUENCE, 5);
    return term_str;
}

Msg parse_server_message(char *buf) {
    Msg msg = {0};

    // backup buf to ease inter-process communication
    size_t len = strlen(buf);
    // remember to free after sending msg.buf to xterm chat
    msg.buf = malloc(len+1);
    strncpy(msg.buf, buf, len+1);

    // terminate the first word
    char *space_loc = strchr(buf, ' ');
    if (space_loc != NULL) {
        *space_loc = 0;
    }

    // TODO: finalize each msg parsing
    if (strcmp(buf, CONNECT_RESPONSE_STR) == 0) {
        msg.command = CONNECT_RESPONSE;

    } else if (strcmp(buf, REGISTER_USERNAME_RESPONSE_TAKEN_STR) == 0) {
        msg.command = REGISTER_USERNAME_RESPONSE_TAKEN;

    } else if (strcmp(buf, REGISTER_USERNAME_RESPONSE_SUCCESS_STR) == 0) {
        msg.command = REGISTER_USERNAME_RESPONSE_SUCCESS;

    } else if (strcmp(buf, DAILY_MESSAGE_STR) == 0) {
        msg.command = DAILY_MESSAGE;
        msg.message = ++space_loc;

    } else if (strcmp(buf, LIST_USERS_RESPONSE_STR) == 0) {
        msg.command = LIST_USERS_RESPONSE;
        // parse userlist
        // might want to refactor to return the list
        // remember to free
        parse_user_list(++space_loc, &msg.users);

        // int i = 0;
        // while(msg.users[i]) {
        //     debug(msg.users[i++]);
        // }

    } else if (strcmp(buf, SEND_MESSAGE_RESPONSE_SUCCESS_STR) == 0) {
        msg.command = SEND_MESSAGE_RESPONSE_SUCCESS;
        msg.username = ++space_loc;

    } else if (strcmp(buf, SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST_STR) == 0) {
        msg.command = SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST;
        msg.username = ++space_loc;

    } else if (strcmp(buf, RECEIVE_MESSAGE_STR) == 0) {
        msg.command = RECEIVE_MESSAGE;
        msg.username = ++space_loc;

        space_loc = strchr(space_loc, ' ');
        if (space_loc == NULL) {
            exit_error("Malformed FROM message");
        }
        *space_loc = 0;

        msg.message = ++space_loc;

    } else if (strcmp(buf, LOGOUT_RESPONSE_STR) == 0) {
        msg.command = LOGOUT_RESPONSE;

    } else if (strcmp(buf, USER_LOGGED_OFF_STR) == 0) {
        msg.command = USER_LOGGED_OFF;
        msg.username = ++space_loc;

    } else {
        exit_error(INVALID_PROTOCOL_MESSAGE);
    }

    return msg;
}

int encode_message(char **buf, Msg msg) {
    int message_length = 0;
    int cmd_length = 0;
    int username_length = 0;

    switch (msg.command) {
        case CONNECT:
            cmd_length = strlen(CONNECT_STR);
            message_length = cmd_length + END_OF_MESSAGE_SEQUENCE_LENGTH + 1;

            // as long as we allocate length + 1, we don't have to insert null-terminator
            *buf = calloc(message_length, 1);
            snprintf(*buf, message_length, "%s%s",
                     CONNECT_STR,
                     END_OF_MESSAGE_SEQUENCE);

            break;

        case REGISTER_USERNAME:
            cmd_length = strlen(REGISTER_USERNAME_STR);
            username_length = strlen(msg.username);
            message_length = cmd_length + username_length + END_OF_MESSAGE_SEQUENCE_LENGTH + 2;

            *buf = calloc(message_length, 1);
            snprintf(*buf, message_length, "%s %s%s",
                     REGISTER_USERNAME_STR,
                     msg.username,
                     END_OF_MESSAGE_SEQUENCE);
            break;

        case LIST_USERS:
            cmd_length = strlen(LIST_USERS_STR);
            message_length = cmd_length + END_OF_MESSAGE_SEQUENCE_LENGTH + 1;

            *buf = calloc(message_length, 1);
            snprintf(*buf, message_length, "%s%s",
                     LIST_USERS_STR,
                     END_OF_MESSAGE_SEQUENCE);
            break;

        case SEND_MESSAGE:
            cmd_length = strlen(SEND_MESSAGE_STR);
            username_length = strlen(msg.username);
            int user_message_length = strlen(msg.message);
            message_length = cmd_length + username_length + user_message_length + END_OF_MESSAGE_SEQUENCE_LENGTH + 3;

            *buf = calloc(message_length, 1);
            snprintf(*buf, message_length, "%s %s %s%s",
                     SEND_MESSAGE_STR,
                     msg.username,
                     msg.message,
                     END_OF_MESSAGE_SEQUENCE);
            break;

        case RECEIVE_MESSAGE_SUCCESS:
            cmd_length = strlen(RECEIVE_MESSAGE_SUCCESS_STR);
            username_length = strlen(msg.username);
            message_length = cmd_length + username_length + END_OF_MESSAGE_SEQUENCE_LENGTH + 2;

            *buf = calloc(message_length, 1);
            snprintf(*buf, message_length, "%s %s%s",
                     RECEIVE_MESSAGE_SUCCESS_STR,
                     msg.username,
                     END_OF_MESSAGE_SEQUENCE);
            break;

        case LOGOUT:
            cmd_length = strlen(LOGOUT_STR);
            message_length = cmd_length + END_OF_MESSAGE_SEQUENCE_LENGTH + 1;

            *buf = calloc(message_length, 1);
            snprintf(*buf, message_length, "%s%s",
                     LOGOUT_STR,
                     END_OF_MESSAGE_SEQUENCE);
            break;

    }
    return message_length;
}

void send_message(int socket_fd, Msg msg) {
    // encode message
    char *encoded_message;
    int n = encode_message(&encoded_message, msg);

    // send message
    write(socket_fd, encoded_message, n);

    // free buffer
    free(encoded_message);
}


void process_messsage(ApplicationState* app_state, Msg* msg) {
    switch (msg->command) {
        // TODO: should we have all the message types here (even outgoing)?

        case CONNECT_RESPONSE:
            debug("CONNECT_RESPONSE");
            if (app_state->connection_state != CONNECTING) {
                exit_error(UNREQUESTED_PROTOCOL_MESSAGE);
            }

            app_state->connection_state = CONNECTED;

            Msg new_msg = {0};
            new_msg.command = REGISTER_USERNAME;
            new_msg.username = app_state->username;

            send_message(app_state->socket_fd, new_msg);

            app_state->connection_state = REGISTERING_USERNAME;

            break;

        case REGISTER_USERNAME_RESPONSE_TAKEN:
            debug("REGISTER_USERNAME_RESPONSE_TAKEN");
            if (app_state->connection_state != REGISTERING_USERNAME) {
                exit_error(UNREQUESTED_PROTOCOL_MESSAGE);
            }

            exit_error("Username Taken");

            break;

        case REGISTER_USERNAME_RESPONSE_SUCCESS:
            debug("REGISTER_USERNAME_RESPONSE_SUCCESS");
            if(app_state->connection_state != REGISTERING_USERNAME) {
                exit_error("Unexpected Username Response Sucess Msg");
            }

            // expect MOTD next (can only be received once)
            app_state->connection_state = LOGGED_IN_AWAITING_MOTD;

            break;

        case DAILY_MESSAGE:
            debug("DAILY_MESSAGE");
            if(app_state->connection_state != LOGGED_IN_AWAITING_MOTD) {
                exit_error("Unexpected MOTD");
            }

            app_state->connection_state = LOGGED_IN;

            printf("MOTD: %s\n", msg->message);

            break;

        case LIST_USERS_RESPONSE:
            debug("LIST_USERS_RESPONSE");
            if(app_state->connection_state != LOGGED_IN) {
                exit_error("Unexpected Userlist");
            }

            char** userlist = msg->users;
            printf("%s", "All Connected Users:\n");
            while(*userlist) {
                printf("%s\n", *userlist++);
            }

            break;

        case SEND_MESSAGE_RESPONSE_SUCCESS:
            debug("SEND_MESSAGE_RESPONSE_SUCCESS");
            // this is not entirely true. receiving this message when we
            // didn't ask for it is a protocol error. we need to keep track
            // of all outgoing messages (not too difficult if we only allow
            // terminals to send out one message at a time)
            if(app_state->connection_state != LOGGED_IN) {
                exit_error("Unexpected Send Msg Success Response Msg");
            }

            // do nothing

            break;

        case SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST:
            debug("SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST");
            if(app_state->connection_state != LOGGED_IN)
                exit_error("Unexpected Send Msg DNE Response Msg");

            // TODO: print this in the appropriate window
            printf("Receipient %s does not exist\n", msg->username);

            break;

        case RECEIVE_MESSAGE:
            debug("RECEIVE_MESSAGE");
            if(app_state->connection_state != LOGGED_IN)
                exit_error("Unexpected Message From Another User");

            Msg response = {0};
            response.command = RECEIVE_MESSAGE_SUCCESS;
            response.username = msg->username;

            send_message(app_state->socket_fd, response);

            // SHOULD BE PRINTED IN XTERM INSTANCE
            printf("%s: %s\n", msg->username, msg->message);

            break;

        case LOGOUT_RESPONSE:
            debug("LOGOUT_RESPONSE");
            if(app_state->connection_state != QUITTING)
                exit_error("Unexpected Logout Response");
            // close socket?
            printf("%s\n", "Logout");
            app_state->connection_state = TERMINATE;
            break;

        case USER_LOGGED_OFF:
            debug("USER_LOGGED_OFF");
            if(app_state->connection_state != LOGGED_IN)
                exit_error("Unexpected User Logout Broadcast");

            break;

    }
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


void parseArgs(int argc, char** argv, int* verbose, char** uname, char** addr, char** port) {
    char *helpMsg =
        "./client [-hv] NAME SERVER_IP SERVER_PORT\n" \
        "-h                         Displays this help menu, and returns EXIT_SUCCESS.\n" \
        "-v                         Verbose print all incoming and outgoing protocol verbs & content.\n" \
        "NAME                       This is the username to display when chatting.\n" \
        "SERVER_IP                  The ip address of the server to connect to.\n" \
        "SERVER_PORT                The port to connect to.\n";

    int c;
    int opterr = 0;

    while((c = getopt(argc, argv, "hv")) != -1) {
        switch(c) {
            case 'h':
                printf("%s", helpMsg);
                exit(EXIT_SUCCESS);
            case 'v':
                *verbose = 1;
                break;
            default:
                exit_error(helpMsg);
        }
    }

    if(optind >= argc) {
        exit_error(helpMsg);
    }

    // TODO: more error checking
    *uname = argv[optind];
    *addr = argv[optind + 1];
    *port = argv[optind + 2];
}


int read_until_newlines(int fd, char **buf) {
    // check if there's actually something to read
    int bytes_readable;
    ioctl(fd, FIONREAD, &bytes_readable);
    if (bytes_readable == 0) {
        return 0;
    }

    // init buffer
    *buf = calloc(BUF_SIZE, 1);
    int i = 0;

    while (true) {
        // increase buffer size by BUF_SIZE when full
        if (i > 0 && i % BUF_SIZE == 0) {
            *buf = realloc(*buf, i+BUF_SIZE);
            memset(*buf+i, 0, BUF_SIZE);
        }

        // read the bytes into our buffer (possibly in the middle)
        i += read(fd, *buf + i, 1);

        if ((*buf)[i] == EOF) {
            exit_error(SOCKET_CLOSE_ERROR_MESSAGE);
        }

        // check for end of message sequence
        if (i >= 4 && strncmp((*buf+i-4), END_OF_MESSAGE_SEQUENCE, 4) == 0) {
            break;
        }
    }

    // remove trailing newlines and insert null-terminator
    (*buf)[i - 4] = 0;

    // num chars read
    return i - 4;
}


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
        // TODO: check for stale requests
        // e.g. requests we made that didn't receive a response
        // if this happens, we should probably exit


        int n_events = poll(poll_fds, 2, -1);

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