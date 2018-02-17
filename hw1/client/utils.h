#ifndef UTILS_H
#define UTILS_H

void exit_error(char *msg);

void debug(char *msg);

int parse_user_list(char* buf, char*** users);

void parseArgs(int argc, char** argv, int* verbose, char** uname, char** addr, char** port);

int read_until_terminator(int fd, char **buf, char *terminator);

#endif