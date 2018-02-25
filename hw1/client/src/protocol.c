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

    // parse the message
    if (strcmp(buf, CONNECT_RESPONSE_STR) == 0) {
        msg.command = CONNECT_RESPONSE;
        msg.outgoing = false;

    } else if (strcmp(buf, REGISTER_USERNAME_RESPONSE_TAKEN_STR) == 0) {
        msg.command = REGISTER_USERNAME_RESPONSE_TAKEN;
        msg.outgoing = false;

    } else if (strcmp(buf, REGISTER_USERNAME_RESPONSE_SUCCESS_STR) == 0) {
        msg.command = REGISTER_USERNAME_RESPONSE_SUCCESS;
        msg.outgoing = false;

    } else if (strcmp(buf, DAILY_MESSAGE_STR) == 0) {
        msg.command = DAILY_MESSAGE;
        msg.message = ++space_loc;
        msg.outgoing = false;

    } else if (strcmp(buf, LIST_USERS_RESPONSE_STR) == 0) {
        msg.command = LIST_USERS_RESPONSE;
        msg.outgoing = false;
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
        msg.outgoing = false;

    } else if (strcmp(buf, SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST_STR) == 0) {
        msg.command = SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST;
        msg.username = ++space_loc;
        msg.outgoing = false;

    } else if (strcmp(buf, RECEIVE_MESSAGE_STR) == 0) {
        msg.command = RECEIVE_MESSAGE;
        msg.username = ++space_loc;
        msg.outgoing = false;

        space_loc = strchr(space_loc, ' ');
        if (space_loc == NULL) {
            exit_error("Malformed FROM message");
        }
        *space_loc = 0;

        msg.message = ++space_loc;

    } else if (strcmp(buf, LOGOUT_RESPONSE_STR) == 0) {
        msg.command = LOGOUT_RESPONSE;
        msg.outgoing = false;

    } else if (strcmp(buf, USER_LOGGED_OFF_STR) == 0) {
        msg.command = USER_LOGGED_OFF;
        msg.username = ++space_loc;
        msg.outgoing = false;

    } else {
        exit_error(INVALID_PROTOCOL_MESSAGE);
    }

    return msg;
}

Msg parse_user_message(char *buf) {
    Msg msg = {0};

    // terminate the first word
    char *space_loc = strchr(buf, ' ');
    if (space_loc != NULL) {
        *space_loc = 0;
    }

    // parse the message
    if (strcmp(buf, CLIENT_HELP_STR) == 0) {
        msg.command = HELP;

    } else if (strcmp(buf, CLIENT_LOGOUT_STR) == 0) {
        msg.command = LOGOUT;
        msg.outgoing = true;

    } else if (strcmp(buf, CLIENT_LISTU_STR) == 0) {
        msg.command = LIST_USERS;
        msg.outgoing = true;

    } else if (strcmp(buf, CLIENT_CHAT_STR) == 0) {
        if (space_loc == NULL) {
            exit_error("Malformed /chat message");
        }

        msg.command = SEND_MESSAGE;
        msg.username = ++space_loc;
        msg.outgoing = true;

        space_loc = strchr(space_loc, ' ');
        if (space_loc == NULL) {
            exit_error("Malformed /chat message");
        }
        *space_loc = 0;

        msg.message = ++space_loc;

        if (strlen(msg.username) > 10) {
            exit_error(USERNAME_TOO_LONG_ERROR);
        }

    } else {
        msg.command = INVALID_USER_INPUT;
    }

    return msg;
}

Msg parse_window_message(char *buf) {
    Msg msg = {0};

    // terminate the first word
    char *space_loc = strchr(buf, ' ');
    if (space_loc != NULL) {
        *space_loc = 0;
    }

    // parse the message
    if (strcmp(buf, SEND_MESSAGE_STR) == 0) {
        msg.command = SEND_MESSAGE;
        msg.outgoing = true;
        msg.username = ++space_loc;

        space_loc = strchr(space_loc, ' ');
        if (space_loc == NULL) {
            exit_error("Malformed /chat message");
        }
        *space_loc = 0;
        msg.message = ++space_loc;
    } else if (strcmp(buf, XTERM_EXIT_STR) == 0) {
        msg.command = XTERM_CLOSE;
        msg.username = ++space_loc;
    } else {
        msg.command = XTERM_BAD_MSG;
        exit_error("bad message from chat to client");
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

        default:
            exit_error("Invalid outgoing message passed to encoder.");
            break;

    }
    return message_length - 1;
}

void send_message(ApplicationState *app_state, Msg msg) {
    // store the message if it's outgoing
    if (msg.outgoing) {
        OutgoingConnection *conn = calloc(sizeof(OutgoingConnection), 1);
        conn->msg = msg;
        conn->next = app_state->next_conn;
        app_state->next_conn = conn;
    }

    // encode message
    char *encoded_message;
    int n = encode_message(&encoded_message, msg);

    // send message
    // TODO: Handle EINTR?
    int stat;
    if((stat = write(app_state->socket_fd, encoded_message, n)) < 0) {
        exit_error("write error");
    }

    // free buffer
    free(encoded_message);
}


void process_messsage(ApplicationState* app_state, Msg* msg) {
    switch (msg->command) {
        case CONNECT_RESPONSE:
            debug("CONNECT_RESPONSE");
            if (app_state->connection_state != CONNECTING
                || !find_matching_connection(app_state, msg)) {
                exit_error(UNREQUESTED_PROTOCOL_MESSAGE);
            }

            app_state->connection_state = CONNECTED;

            Msg new_msg = {0};
            new_msg.command = REGISTER_USERNAME;
            new_msg.username = app_state->username;
            new_msg.outgoing = true;

            send_message(app_state, new_msg);

            app_state->connection_state = REGISTERING_USERNAME;

            break;

        case REGISTER_USERNAME_RESPONSE_TAKEN:
            debug("REGISTER_USERNAME_RESPONSE_TAKEN");
            if (app_state->connection_state != REGISTERING_USERNAME
                || !find_matching_connection(app_state, msg)) {
                exit_error(UNREQUESTED_PROTOCOL_MESSAGE);
            }

            exit_error("Username Taken");

            break;

        case REGISTER_USERNAME_RESPONSE_SUCCESS:
            debug("REGISTER_USERNAME_RESPONSE_SUCCESS");
            if(app_state->connection_state != REGISTERING_USERNAME
                || !find_matching_connection(app_state, msg)) {
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

        case INVALID_USER_INPUT:
            printf("%s\n", "Invalid user input");
            break;

        case HELP:
            printf("%s", HELP_MESSAGE);

            break;

        case LIST_USERS:
            debug("LIST_USERS");
            if (app_state->connection_state != LOGGED_IN) {
                exit_error("Cannot request user list until logged in.");
            }

            send_message(app_state, *msg);

            break;

        case LIST_USERS_RESPONSE:
            debug("LIST_USERS_RESPONSE");
            if(app_state->connection_state != LOGGED_IN
                || !find_matching_connection(app_state, msg)) {
                exit_error("Unexpected Userlist");
            }

            char** userlist = msg->users;
            printf("%s", "All Connected Users:\n");
            while(*userlist) {
                printf("%s\n", *userlist++);
            }

            break;

        case SEND_MESSAGE:
            debug("SEND_MESSAGE");
            if (app_state->connection_state != LOGGED_IN)
                exit_error("Not logged in.");

            send_message(app_state, *msg);
            break;

        case SEND_MESSAGE_RESPONSE_SUCCESS:
            debug("SEND_MESSAGE_RESPONSE_SUCCESS");
            if(app_state->connection_state != LOGGED_IN
                || !find_matching_connection(app_state, msg)) {
                exit_error("Unexpected Send Msg Success Response Msg");
            }

            // only open window if other user exists
            // TODO find the msg that was sent and write it to xterm
            ChatWindow *window = create_or_get_window(app_state, msg->username);
            write(window->parent_to_child[1], msg->buf, strlen(msg->buf));
            write(window->parent_to_child[1], END_OF_MESSAGE_SEQUENCE, 4);

            break;

        case SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST:
            debug("SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST");
            if(app_state->connection_state != LOGGED_IN
                || !find_matching_connection(app_state, msg))
                exit_error("Unexpected Send Msg DNE Response Msg");

            printf("Receipient %s does not exist\n", msg->username);

            break;

        case RECEIVE_MESSAGE:
            debug("RECEIVE_MESSAGE");
            if(app_state->connection_state != LOGGED_IN)
                exit_error("Unexpected Message From Another User");

            // send message internally to xterm client
            ChatWindow *xterm_window = create_or_get_window(app_state, msg->username);
            write(xterm_window->parent_to_child[1], msg->buf, strlen(msg->buf));
            write(xterm_window->parent_to_child[1], END_OF_MESSAGE_SEQUENCE, 4);

            // server response
            Msg response = {0};
            response.command = RECEIVE_MESSAGE_SUCCESS;
            response.username = msg->username;
            response.outgoing = false;

            send_message(app_state, response);

            break;

        case LOGOUT:
            debug("LOGOUT");
            if (app_state->connection_state != LOGGED_IN)
                exit_error("Cannot logout if not logged in!");

            send_message(app_state, *msg);
            printf("%s\n", "Logging out");

            app_state->connection_state = QUITTING;
            break;

        case LOGOUT_RESPONSE:
            debug("LOGOUT_RESPONSE");
            if(app_state->connection_state != QUITTING
                || !find_matching_connection(app_state, msg))
                exit_error("Unexpected Logout Response");

            printf("%s\n", "Logged out");
            app_state->connection_state = TERMINATE;
            break;

        case USER_LOGGED_OFF:
            debug("USER_LOGGED_OFF");
            if(app_state->connection_state != LOGGED_IN)
                exit_error("Unexpected User Logout Broadcast");

            // print user logged off message
            break;

        case XTERM_CLOSE:
            remove_window(app_state, msg->username);
            break;

        default:
            exit_error("Received an unexpected protocol message.");
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
