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

        default:
            exit_error("Invalid outgoing message passed to encoder.");
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
            if(app_state->connection_state != LOGGED_IN) {
                exit_error("Unexpected Send Msg Success Response Msg");
            }

            // TODO: forward this message to the appropriate xterm window

            break;

        case SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST:
            debug("SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST");
            if(app_state->connection_state != LOGGED_IN)
                exit_error("Unexpected Send Msg DNE Response Msg");

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

            // TODO: SHOULD BE PRINTED IN XTERM INSTANCE
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

            // print user logged off message
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
