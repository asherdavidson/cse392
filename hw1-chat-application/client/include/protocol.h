#ifndef PROTOCOL_H
#define PROTOCOL_H

Msg parse_server_message(char *buf);

Msg parse_user_message(char *buf);

Msg parse_window_message(char *buf);

int encode_message(char **buf, Msg msg);

void send_message(ApplicationState *app_state, Msg msg);

void process_messsage(ApplicationState* app_state, Msg* msg);

int init_socket(const char *address, const char *port);



#endif
