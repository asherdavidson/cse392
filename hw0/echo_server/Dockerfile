# Use gcc as the parent image
FROM gcc:7

# Set the working directory to /echo
WORKDIR /echo

# Copy the contents of the current directory to /echo
ADD . /echo

# Compile the code
RUN make clean all

# Run the echo_server
CMD ./echo_server 5000
