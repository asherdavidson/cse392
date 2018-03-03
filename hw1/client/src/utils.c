#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <errno.h>
#include <poll.h>
#include <math.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <stdbool.h>

#include "types.h"
#include "utils.h"

void exit_error(char *msg) {
    printf("\x1B[1;31m%s\x1B[0m\n", msg);
    exit(EXIT_FAILURE);
}

void debug(char *msg) {
    // printf("\x1B[1;34m%s\x1B[0m\n", msg);
}

void verbose(char *msg) {
    if (!msg)
        return;

    if (verboseFlag) {
        // remove end of line terminator
        char *end = strstr(msg, END_OF_MESSAGE_SEQUENCE);
        if (end) {
            int len = (int)(end - msg);
            char buf[len+1];
            strncpy(buf, msg, len);
            buf[len] = 0;
            printf("\x1B[1;34m%s\x1B[0m\n", buf);

        } else {
            printf("\x1B[1;34m%s\x1B[0m\n", msg);
        }
    }
}

void remove_connection(ApplicationState *app_state, OutgoingConnection *conn) {
    // free mem if needed
    if (conn->msg.message) {
        free(conn->msg.message);
    }

    // remove if head
    if (app_state->next_conn == conn) {
        app_state->next_conn = conn->next;

    // remove in list
    } else {
        OutgoingConnection *prev = app_state->next_conn;
        while (prev->next != conn)
            prev = prev->next;

        prev->next = prev->next->next;
    }

}


// modified to return message for SEND_MESSAGE
bool find_matching_connection(ApplicationState *app_state, Msg *msg, char **previous_msg) {
    OutgoingConnection *conn = app_state->next_conn;

    while (conn) {
        switch (msg->command) {
            case CONNECT_RESPONSE:
                if (conn->msg.command == CONNECT) {
                    remove_connection(app_state, conn);
                    return true;
                }
                break;

            case REGISTER_USERNAME_RESPONSE_TAKEN:
            case REGISTER_USERNAME_RESPONSE_SUCCESS:
                if (conn->msg.command == REGISTER_USERNAME) {
                    remove_connection(app_state, conn);
                    return true;
                }
                break;

            case LIST_USERS_RESPONSE:
                if (conn->msg.command == LIST_USERS) {
                    remove_connection(app_state, conn);
                    return true;
                }
                break;

            case SEND_MESSAGE_RESPONSE_SUCCESS:
                if (!conn->msg.message) {
                    debug("No corresponding message");
                }

                ssize_t len = strlen(conn->msg.message);

                *previous_msg = calloc(len + 1, 1);
                strncpy(*previous_msg, conn->msg.message, len);

            case SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST:
                if (conn->msg.command == SEND_MESSAGE) {
                    remove_connection(app_state, conn);
                    return true;
                }
                break;

            case LOGOUT_RESPONSE:
                if (conn->msg.command == LOGOUT) {
                    remove_connection(app_state, conn);
                    return true;
                }
                break;

            default:
                exit_error("Invalid message type in find_matching_connection");
        }

        conn = conn->next;
    }
    return false;
}

int parse_user_list(char* buf, char*** users) {
    // find the number of users
    int num_users = 1;
    char *buf_ptr = buf;
    while ((buf_ptr = strchr(buf_ptr, ' '))) {
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

void parseArgs(int argc, char** argv, int* verbose, char** uname, char** addr, char** port) {
    char *helpMsg =
        "./client [-hv] NAME SERVER_IP SERVER_PORT\n" \
        "-h                         Displays this help menu, and returns EXIT_SUCCESS.\n" \
        "-v                         Verbose print all incoming and outgoing protocol verbs & content.\n" \
        "NAME                       This is the username to display when chatting.\n" \
        "SERVER_IP                  The ip address of the server to connect to.\n" \
        "SERVER_PORT                The port to connect to.\n";

    int c;
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

    if (strlen(*uname) > 10) {
        exit_error(USERNAME_TOO_LONG_ERROR);
    }
}


int read_until_terminator(int fd, char **buf, char *terminator) {
    int terminator_len = strlen(terminator);

    // init buffer
    *buf = calloc(BUF_SIZE, 1);
    int i = 0;

    while (true) {
        // increase buffer size by BUF_SIZE when full
        if (i > 0 && i % BUF_SIZE == 0) {
            *buf = realloc(*buf, i+BUF_SIZE);
            memset(*buf+i, 0, BUF_SIZE);
        }

        // set up poll data
        struct pollfd poll_fd = {
            .fd = fd,
            .events = POLLIN
        };

        // read can block, so we poll on it for 1s
        switch (poll(&poll_fd, 1, NETWORK_TIMEOUT)) {
            case -1:
                free(*buf);
                exit_error("an error occurred while reading.");

            case 0:
                free(*buf);
                exit_error("an invalid request was made or the request timed out.");

            default: ;
                // read the bytes into our buffer (possibly in the middle)
                ssize_t nread = read(fd, *buf + i, 1);

                if (nread == 0) {
                    free(*buf);
                    exit_error(SOCKET_CLOSE_ERROR_MESSAGE);
                }
                else if (nread < 0 && errno == EINTR)
                    continue;
                else if (nread < 0) {
                    free(*buf);
                    exit_error("read error");
                }

                i += nread;
        }

        // check for end of message sequence
        if (i >= terminator_len && strncmp((*buf+i-terminator_len), terminator, terminator_len) == 0) {
            break;
        }
    }

    // remove trailing newlines and insert null-terminator
    (*buf)[i - terminator_len] = 0;

    // num chars read
    return i - terminator_len;
}

ChatWindow *create_or_get_window(ApplicationState *app_state, char *name) {
    // check if window exists and return
    ChatWindow* curr_window = app_state->next_window;
    while(curr_window) {
        if(!strcmp(curr_window->name, name)) {
            return curr_window;
        }
        curr_window = curr_window->next;
    }

    ChatWindow* new_window = calloc(sizeof(ChatWindow), 1);
    strncpy(new_window->name, name, 11);

    pipe(new_window->parent_to_child);
    pipe(new_window->child_to_parent);

    // insert window into state
    new_window->next = app_state->next_window;
    app_state->next_window = new_window;
    app_state->fds_changed = 1;

    // fork and exec with params
    pid_t pid = fork();
    if(pid < 0) {
        exit_error("fork error");
    } else if (pid == 0) {
        // child
        close(new_window->parent_to_child[1]);
        close(new_window->child_to_parent[0]);

        char read_fd[(int)((ceil(log10(new_window->parent_to_child[0]) + 1))) * sizeof(char)];
        char write_fd[(int)((ceil(log10(new_window->child_to_parent[1]) + 1))) * sizeof(char)];

        sprintf(read_fd,"%d", new_window->parent_to_child[0]);
        sprintf(write_fd, "%d", new_window->child_to_parent[1]);

        execl("/usr/bin/xterm", "xterm", "-T", name, "-e", "bin/chat", name, read_fd, write_fd, NULL);
    }

    close(new_window->parent_to_child[0]);
    close(new_window->child_to_parent[1]);

    return new_window;
}

void remove_window(ApplicationState* app_state, char *name) {
    printf("%s\n", "cleaning up window info");

    bool found = false;
    ChatWindow* prev = NULL;
    ChatWindow* curr = app_state->next_window;

    while(curr) {
        if(!strcmp(name, curr->name)) {
            found = true;

            if(!prev) {
                app_state->next_window = curr->next;
            } else {
                prev->next = curr->next;
                curr->next = NULL;
            }
            close(curr->parent_to_child[1]);
            close(curr->parent_to_child[0]);
            free(curr);
            break;
        } else {
            prev = curr;
            curr = curr->next;
        }
    }

    if(!found) {
        exit_error("no window to clean up");
    }

    app_state->fds_changed = true;
}

void sig_child(int signo) {
    pid_t pid;
    int stat;

    while((pid = waitpid(-1, &stat, WNOHANG)) > 0)
        debug("child terminated");

    return;
}

void sig_pipe(int signo) {
    exit_error("socket closed");
}
