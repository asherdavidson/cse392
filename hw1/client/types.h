#ifndef CLIENT_TYPES_H
#define CLIENT_TYPES_H

#define BUF_SIZE 256
#define MAX_EVENTS 10

#define SOCKET_CLOSE_ERROR_MESSAGE "The connection was closed. Exiting."
#define INVALID_PROTOCOL_MESSAGE "Invalid protocol message. Exiting."
#define UNREQUESTED_PROTOCOL_MESSAGE "A message was received that was not requested. Exiting."

#define END_OF_MESSAGE_SEQUENCE                  "\r\n\r\n"
#define END_OF_MESSAGE_SEQUENCE_LENGTH           4

#define CONNECT_STR                              "ME2U"
#define CONNECT_RESPONSE_STR                     "U2EM"
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
    CONNECT,
    CONNECT_RESPONSE,
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
    char *buf;
} Msg;

typedef enum {
    CONNECTING,
    CONNECTED,
    REGISTERING_USERNAME,
    LOGGED_IN_AWAITING_MOTD,
    LOGGED_IN,
    QUITTING,
    TERMINATE
} ConnectionState;

typedef struct {
    ConnectionState connection_state;
    int socket_fd;
    char *username;
} ApplicationState;

#endif