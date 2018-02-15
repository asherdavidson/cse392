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

#define BUF_SIZE 256
#define MAX_EVENTS 10

#define INVALID_PROTOCOL_MESSAGE "Invalid protocol message. Exiting."

char *END_OF_MESSAGE_SEQUENCE = "\r\n\r\n";

#define LOGIN_STR                                "ME2U"
#define LOGIN_RESPONSE_STR                       "U2EM"
#define REGISTER_USERNAME_STR                    "IAM"
#define REGISTER_USERNAME_RESPONSE_TAKEN_STR     "ETAKEN"
#define REGISTER_USERNAME_RESPONSE_SUCCESS_STR   "MAI"
#define DAILY_MESSAGE_STR                        "MOTD"
#define LIST_USERS_STR                           "LISTU"
#define LIST_USERS_RESPONSE_STR                  "UTSIL"
#define SEND_MESSAGE_STR                         "TO"
#define SEND_MESSAGE_RESPONSE_SUCCESS_STR        "OT"
#define SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST_STR "EDNE"
#define RECEIVE_MESSAGE_STR                      "FROM"
#define RECEIVE_MESSAGE_SUCCESS_STR              "MORF"
#define LOGOUT_STR                               "BYE"
#define LOGOUT_RESPONSE_STR                      "EYB"
#define USER_LOGGED_OFF_STR                      "UOFF"

#define CLIENT_LOGOUT "/logout"
#define CLIENT_HELP   "/help"
#define CLIENT_LISTU  "/listu"
#define CLIENT_CHAT   "/chat"

typedef enum {
    LOGIN,
    LOGIN_RESPONSE,
    REGISTER_USERNAME,
    REGISTER_USERNAME_RESPONSE_TAKEN,
    REGISTER_USERNAME_RESPONSE_SUCCESS,
    DAILY_MESSAGE,
    LIST_USERS,
    LIST_USERS_RESPONSE,
    SEND_MESSAGE,
    SEND_MESSAGE_RESPONSE_SUCCESS,
    SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST,
    RECEIVE_MESSAGE,
    RECEIVE_MESSAGE_SUCCESS,
    LOGOUT,
    LOGOUT_RESPONSE,
    USER_LOGGED_OFF
} Cmd;

typedef struct protocol_message {
    Cmd command;
    char *username;
    char *message;
    char **users; // {&"asd", &"qwe"}
    char *to;
    char *from;
    char *buf;
} Msg;

void exit_error(char *msg) {
    printf("\x1B[1;31m%s\x1B[0m\n", msg);
    exit(EXIT_FAILURE);
}

void debug(char *msg) {
    printf("\x1B[1;34m%s\x1B[0m\n", msg);
}

Msg parse_server_message(char *buf) {
    Msg msg;

    // backup buf to ease inter-process communication
    size_t len = strlen(buf);
    // remember to free after sending msg.buf to xterm chat
    msg.buf = malloc(len);
    strncpy(msg.buf, buf, len);

    // terminate the first word
    char *space_loc = strchr(buf, ' ');
    if (space_loc != NULL) {
        *space_loc = 0;
    }

    // TODO: finalize each msg parsing
    if (strcmp(buf, LOGIN_RESPONSE_STR) == 0) {
        msg.command = LOGIN_RESPONSE;

    } else if (strcmp(buf, REGISTER_USERNAME_RESPONSE_TAKEN_STR) == 0) {
        // need to know what user typed as username since server doesn't return it
        msg.command = REGISTER_USERNAME_RESPONSE_TAKEN;

    } else if (strcmp(buf, REGISTER_USERNAME_RESPONSE_SUCCESS_STR) == 0) {
        msg.command = REGISTER_USERNAME_RESPONSE_SUCCESS;

    } else if (strcmp(buf, DAILY_MESSAGE_STR) == 0) {
        msg.command = DAILY_MESSAGE;
        msg.message = ++space_loc;

    } else if (strcmp(buf, LIST_USERS_RESPONSE_STR) == 0) {
        msg.command = LIST_USERS_RESPONSE;
        // parse users

    } else if (strcmp(buf, SEND_MESSAGE_RESPONSE_SUCCESS_STR) == 0) {
        msg.command = SEND_MESSAGE_RESPONSE_SUCCESS;

    } else if (strcmp(buf, SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST_STR) == 0) {
        msg.command = SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST;
        msg.username = ++space_loc;

    } else if (strcmp(buf, RECEIVE_MESSAGE_STR) == 0) {
        msg.command = RECEIVE_MESSAGE;

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
    // init buffer
    *buf = calloc(BUF_SIZE, 1);
    int cnt; // used in ioctl (size of input to read)
    int i = 0;

    // check if there's actually something to read
    if (ioctl(fd, FIONREAD, &cnt) == 0 && cnt > 0) {
        char c = 0;

        while (true) {
            // increase buffer size by BUF_SIZE when full
            if (i > 0 && i % BUF_SIZE == 0) {
                *buf = realloc(*buf, i+BUF_SIZE);
                memset(*buf+i, 0, BUF_SIZE);
            }

            // read the bytes into our buffer (possibly in the middle)
            i += read(fd, *buf + i, BUF_SIZE);

            // check for end of message sequence
            if (i >= 4 && strncmp((*buf+i-4), END_OF_MESSAGE_SEQUENCE, 4) == 0) {
                break;
            }
        }

    // nothing to read
    } else {
        free(*buf);
        return 0;
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

    char *socket_buf;
    char stdin_buf[BUF_SIZE];
    memset(&socket_buf, 0, sizeof(socket_buf));
    memset(&stdin_buf, 0, sizeof(stdin_buf));

    int cnt = 0;

    while (true) {
        int n_events = poll(poll_fds, 2, -1);

        // socket read
        if (poll_fds[0].revents & POLLIN) {
            // debug("socket in");

            // blocks until double newlines
            int n = read_until_newlines(socket_fd, &socket_buf);
            if (n > 0) {
                Msg message = parse_server_message(socket_buf);
                printf("%s\n", socket_buf);
                free(socket_buf);
                // write(STDOUT_FILENO, socket_buf, n);
            }
        }

        if (poll_fds[1].revents & POLLIN) {
            // debug("stdin in");

            memset(&stdin_buf, 0, sizeof(stdin_buf));
            if (ioctl(STDIN_FILENO, FIONREAD, &cnt) == 0 && cnt > 0) {
                int n = read(STDIN_FILENO, &stdin_buf, BUF_SIZE);
                write(socket_fd, &stdin_buf, n);
            }

        }
    }


    // good bye
    close(socket_fd);

    return EXIT_SUCCESS;
}