#include <stdio.h>
#include <stdlib.h>


int main(int argc, char *argv[]) {
    char *name = argv[1];
    int read_fd = atoi(argv[2]);
    int write_fd = atoi(argv[3]);

    printf("%s, %d, %d \n", name, read_fd, write_fd);

    while(1) {

    }

    return 0;
}
