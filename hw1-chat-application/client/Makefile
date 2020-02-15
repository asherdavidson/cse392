CC := gcc
SRCD := src
BLDD := build
BIND := bin
INCD := include

ALL_SRCF := $(shell find $(SRCD) -type f -name *.c)
ALL_OBJF := $(patsubst $(SRCD)/%,$(BLDD)/%,$(ALL_SRCF:.c=.o))
CLIENT_OBJF := $(filter-out build/chat.o, $(ALL_OBJF))
CHAT_OBJF := $(filter-out build/client.o, $(ALL_OBJF))

INC := -I $(INCD)

CLIENT_EXEC := client
CHAT_EXEC := chat

CFLAGS := -Wall -Werror
DFLAGS := -g -DDEBUG -DCOLOR
STD := -std=gnu11
LIBS := -lm

CFLAGS += $(STD)

.PHONY: clean all

debug: CFLAGS += $(DFLAGS)
debug: all

all: setup $(CLIENT_EXEC) $(CHAT_EXEC)

setup:
	mkdir -p bin build

$(CLIENT_EXEC): $(CLIENT_OBJF)
	$(CC) $^ -o $(BIND)/$@ $(LIBS)

$(CHAT_EXEC): $(CHAT_OBJF)
	$(CC) $^ -o $(BIND)/$@ $(LIBS)

$(BLDD)/%.o: $(SRCD)/%.c
	$(CC) $(CFLAGS) $(INC) -c -o $@ $<

clean:
	$(RM) -r $(BLDD) $(BIND)