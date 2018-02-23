#ifndef UTILS_H
#define UTILS_H

#include "types.h"

void exit_error(char *msg);

void debug(char *msg);

bool find_matching_connection(ApplicationState *app_state, Msg *msg);

int parse_user_list(char* buf, char*** users);

void parseArgs(int argc, char** argv, int* verbose, char** uname, char** addr, char** port);

int read_until_terminator(int fd, char **buf, char *terminator);

ChatWindow *create_or_get_window(ApplicationState *app_state, char *name);

// Signal Handlers
void sig_child(int signo);

void sig_pipe(int signo);


#endif
